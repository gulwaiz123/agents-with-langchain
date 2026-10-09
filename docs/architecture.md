# Architecture — Learning Companion Chatbot

A small classroom capstone for a beginner LangChain and LangGraph course.

## Classroom flow

`Open WebUI → this local application’s OpenAI-compatible chat endpoint → LangChain prompt and Gemini model → answer in Open WebUI`

1. The participant types a message in Open WebUI.
2. Open WebUI sends it to this local app at `POST /v1/chat/completions`.
3. The app runs one LangChain flow: prompt → Gemini chat model → text output.
4. The app returns the reply in OpenAI-compatible form (plain JSON, or text-only SSE chunks when streaming).
5. The answer appears in Open WebUI.

## Open WebUI

- Already installed and working for participants.
- It is the supplied chat client only.
- Participants do not reinstall, reconfigure, modify or build it.
- If its existing connection needs a different local base URL or model selection, that value is documented in this project’s `README.md`. Open WebUI itself is not changed.

## What we build

- A small **Learning Companion Chatbot** backend.
- Not a custom frontend. Not a second demonstration application.

## Endpoints

| Route | Purpose |
|---|---|
| `GET /health` | Simple liveness check. Works without an API key. |
| `GET /v1/models` | Lists the configured Gemini model so Open WebUI can select it. |
| `POST /v1/chat/completions` | OpenAI-compatible chat. Accepts `model`, text `messages` (roles `system`, `user`, `assistant`) and `stream`. |

No custom Open WebUI events, no second chat route, no browser UI.

## Stack

Python 3.12, UV, FastAPI, Uvicorn, Pydantic settings, `langchain`, the Gemini LangChain provider integration (`langchain-google-genai`), Ruff, and a minimal test runner.

## Settings (`.env.example`)

```
APP_ENV=development
GEMINI_API_KEY=
GEMINI_MODEL_NAME=
HOST=127.0.0.1
PORT=8000
```

The instructor supplies the model name. Participants put their real key only in the untracked `.env`. The app starts without a key and returns a clear configuration error only when a model call is attempted.

## Light boundaries

- API keys stay in an untracked `.env`.
- Application instructions stay separate from user messages.
- Out of scope: authentication, authorization, security hardening, databases, persistent memory, RAG, production deployment and extensive tests.

## Planned layout

```
src/learning_companion/   config.py, chain.py, main.py
tests/                    one tiny health test at most
```

## Message flow (Stories 2.1 and 2.2)

```
Open WebUI request (messages of the active chat)
  → latest user message + up to 10 earlier user/assistant messages, in order
    (client "system" messages and empty content are skipped)
  → [system: Learning Companion instruction (app-owned), history, human: latest message]
  → Gemini → text answer → OpenAI-compatible JSON or SSE
```

- History comes only from the current request. Limit: the 10 most recent earlier messages (`MAX_HISTORY_MESSAGES`).
- No-persistence boundary: nothing is stored or remembered after a request finishes. No database, cache or cross-session memory. A new chat starts fresh.
- In development (`APP_ENV=development`), `dev_log.py` prints a readable request block (payload, role sequence, messages sent to the model) and a reply block (text, time). Settings and API keys are never logged.

## The `/study` routing rule (Story 3.2)

```
Open WebUI request → latest user message
  → if it starts with "/study": strip that marker → study helper chain
  → else: general chat chain
  → text answer, starting with a label "[route: general]" or "[route: study]"
```

The rule is `choose_route` in `routing.py`: ordinary Python, no model involved. Both chains share the same history and the same normal/streaming adapter. The route is also logged in development. Boundary: this is deterministic application routing, not LLM classification, LangGraph or multi-agent orchestration. Story 4.1 replaces the `if/else` with an explicit LangGraph route.

## Chain behaviours (Story 3.1)

| Chain | Responsibility | Used by the endpoint? |
|---|---|---|
| General chat (`build_chain`) | Greetings and ordinary conversation. | Yes, for every other message. |
| Study helper (`build_study_helper_chain`) | Plain-language explanation of a beginner technical idea, a small example where useful, and one next learning step. Does not search, browse or retrieve course data. | Yes, for messages starting with `/study` (Story 3.2). Also available via `uv run python -m learning_companion.try_study_helper "<question>"`. |

Both use the same prompt shape (application instruction, history, current message), the same configured Gemini model and the same history handling. Story 3.1 creates the study-helper capability only; choosing between the chains is the next story.

## Story 1.1 scope

One fixed Learning Companion instruction plus the latest user message, behind the same chat endpoint for normal and streaming requests. Story 2.1 turned this into a reusable prompt template; conversation history arrives in Story 2.2.
