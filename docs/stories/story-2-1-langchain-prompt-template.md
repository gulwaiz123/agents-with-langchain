# Story 2.1 — LangChain prompt template

## Purpose

Turn the seed's one-line prompt into a small, clear LangChain prompt. The prompt keeps the app's own Learning Companion instruction separate from what the participant types. This keeps the chatbot's behaviour stable and easy to read before history is added in Story 2.2.

## What this story implements in plain English

- The chatbot answers in the same friendly Learning Companion style every time.
- What you type is always treated as your question, never as a change to the chatbot's rules.
- If a chat sends its own "system" text, the chatbot treats it as part of your message, not as a new rulebook.
- Open WebUI looks and works exactly as before: same connection, same model, same replies, streaming still works.
- The chatbot still answers only your latest message. It does not remember earlier ones yet.

## Prerequisites

- Story 1.1 is done and approved. `docs/architecture.md`, the working API and the Open WebUI connection exist.
- The provider is **Gemini** (`GEMINI_API_KEY`, `GEMINI_MODEL_NAME` in `.env`). The Story 1.1 seed was originally written for Grok and was switched to Gemini; keep the current Gemini settings and package unchanged.
- Read first: `docs/config.yaml` (if present), `docs/architecture.md`, Story 1.1, `.env.example`, and the current code in `src/learning_companion/` (`chain.py`, `main.py`, `config.py`).
- Preserve existing work, routes, settings and the working Open WebUI connection. No new dependencies are expected.

## Work to do

1. In `src/learning_companion/chain.py`, replace the fixed latest-message prompt with a small LangChain chat prompt (`ChatPromptTemplate` built from message templates) with exactly two clearly separate parts:
   - a stable Learning Companion **system** instruction owned by the application (keep it as one named constant);
   - the current **human** message, filled in from a variable.
   Do not build a large ad-hoc string by concatenation.
2. Keep the existing chain: prompt → Gemini model → text output. Use it for both the normal and the streaming path. Keep the existing missing-setting configuration error.
3. In `src/learning_companion/main.py`, keep using only the latest supported `user` message from the request. A request-supplied `system` message (or `assistant` message) is user-provided content: it must never replace or be added to the application's system instruction. Do not handle history; Story 2.2 does that.
4. Add a readable development-only log (only when `APP_ENV=development`, in `src/learning_companion/dev_log.py`) printed as a boxed block per request. The request block shows the request id, model, stream flag, the prompt role sequence and message count, the full request payload as indented JSON, and each message sent to the model in order. A reply block shows the id, mode (normal or streamed), time taken and the reply text. Long message bodies are clipped at 2000 characters. It must never print the API key or any settings.
5. Keep `GET /health`, `GET /v1/models` and `POST /v1/chat/completions` unchanged in route, request shape, normal JSON and SSE behaviour, settings and `.env.example`.
6. Update `docs/architecture.md`:
   - add the message flow: Open WebUI request → latest user message → `[system instruction, human message]` → Gemini → text answer;
   - state the deliberate no-persistence boundary (nothing is stored or remembered between requests).
7. Do not add a command-line-only chatbot, a second chat path, conversation history, a database, persistent memory, RAG, tools, MCP, LangGraph, a new frontend, an evaluation harness, a broad test suite, or a security programme.

## Completion checks

Run only these and report the commands you actually ran:

```
uv run ruff format .
uv run ruff check .
uv run uvicorn learning_companion.main:app --host 127.0.0.1 --port 8000
```

Then, in the existing Open WebUI chat (restart the API after any `.env` change):

- [ ] Ask one ordinary question, for example "What is a variable?". A friendly Learning Companion style answer appears and streams normally.
- [ ] The development log shows a request block (payload and messages in order: system, then human) and a reply block. No API key appears.
- [ ] A system message sent by the client does not change the application's instruction.
- [ ] `/health`, `/v1/models` and the Open WebUI connection work as before.
- [ ] `docs/architecture.md` shows the message flow and the no-persistence boundary.

Expected Open WebUI result: one Gemini reply in the Learning Companion style, rendered as before.

## Handover

Files this story changes:

- `src/learning_companion/chain.py` (prompt template and system instruction constant)
- `src/learning_companion/main.py` (latest-user-message selection, development log calls)
- `src/learning_companion/dev_log.py` (new, readable development log)
- `docs/architecture.md` (message flow, no-persistence boundary)

Story 2.2 will extend this by adding conversation history to the same prompt, between the system instruction and the current user message. The routes, settings and Open WebUI connection stay as they are.
