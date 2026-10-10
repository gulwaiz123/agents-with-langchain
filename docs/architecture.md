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

## The routing and review graph (Stories 4.1 and 4.2)

`src/learning_companion/graph.py` is one small LangGraph workflow with a plain-Python router and one bounded review cycle:

```
START → router ─┬─ general → general_chat ─────────────→ reviewer ─┬─ approve ──────────→ END
                └─ study   → study_helper ─┬─ answer ──→ reviewer  │
                                           └─ bare /study ───────────────────────────────→ END
                                                          reviewer ─┴─ improve (only if revision_count = 0) → improver → reviewer
```

State (the shared notebook):

| Field | Meaning |
|---|---|
| `user_message` | What was just asked (`/study` marker removed by the router). |
| `messages` | Earlier chat messages from this request (history). |
| `route` | `general` or `study`. |
| `draft_answer` | The answer as currently written; the improver replaces it. |
| `review_decision` | `approve` or `improve`. |
| `review_reason` | One short sentence from the reviewer. |
| `revision_count` | Rewrites so far: starts at 0, never above 1. |
| `final_answer` | The reply sent to Open WebUI, written only when finishing. |

| Node | Kind | Single responsibility |
|---|---|---|
| `router` | Ordinary Python, not an agent | Applies the `/study` rule, strips the marker, writes `route`. |
| `general_chat` | LLM specialist | Writes a draft using the general-chat chain. |
| `study_helper` | LLM specialist | Writes a draft using the study-helper chain. A bare `/study` writes a fixed reply straight to `final_answer` (no model, no review). |
| `reviewer` | LLM specialist | Checks the draft against one short fixed classroom rule and returns a structured `approve`/`improve` plus one reason. When `revision_count` is 1 it makes no model call and accepts the current draft. |
| `improver` | LLM specialist | Rewrites the draft once using the reviewer's reason and increments `revision_count`. No tools, browsing, retrieval, planning or routing. |

Edge rules: `START → router`; conditional from `router` on `route`; each answer node → `reviewer`; `approve → END`; `improve → improver` only while `revision_count` is 0; `improver → reviewer`. The one visible cycle is reviewer → improver → reviewer, so there is at most one improvement. There is no other loop, retry, planner, tool or open-ended agent behaviour.

The endpoint adds the `[route: ...]` label to `final_answer` and returns it as normal JSON, or as text-only SSE chunks ending with `data: [DONE]` (the finished answer is sent in small chunks). In development the log shows the route, node sequence, review decision and reason, and revision count (never keys or settings).

Scope boundary: no databases, persistence, RAG, web search, tool execution, MCP, human approval or extra agents. A node is a focused piece of work, not automatically an agent. An MCP call could live inside a future node but is not implemented.

## The `/study` routing rule (Story 3.2)

```
Open WebUI request → latest user message
  → if it starts with "/study": strip that marker → study helper chain
  → else: general chat chain
  → text answer, starting with a label "[route: general]" or "[route: study]"
```

The rule is `choose_route` in `routing.py`: ordinary Python, no model involved. Both chains share the same history and the same normal/streaming adapter. The route is also logged in development. Boundary: this is deterministic application routing, not LLM classification, LangGraph or multi-agent orchestration. Story 4.1 moved this rule into the router node of a LangGraph workflow.

## Chain behaviours (Story 3.1)

| Chain | Responsibility | Used by the endpoint? |
|---|---|---|
| General chat (`build_chain`) | Greetings and ordinary conversation. | Yes, for every other message. |
| Study helper (`build_study_helper_chain`) | Plain-language explanation of a beginner technical idea, a small example where useful, and one next learning step. Does not search, browse or retrieve course data. | Yes, for messages starting with `/study` (Story 3.2). Also available via `uv run python -m learning_companion.try_study_helper "<question>"`. |

Both use the same prompt shape (application instruction, history, current message), the same configured Gemini model and the same history handling. Story 3.1 creates the study-helper capability only; choosing between the chains is the next story.

## Story 1.1 scope

One fixed Learning Companion instruction plus the latest user message, behind the same chat endpoint for normal and streaming requests. Story 2.1 turned this into a reusable prompt template; conversation history arrives in Story 2.2.
