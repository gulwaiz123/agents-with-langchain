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

## Story 1.1 scope

One fixed Learning Companion instruction plus the latest user message, behind the same chat endpoint for normal and streaming requests. Full prompt construction and conversation history arrive in Story 2.1.
