# Story 2.2 — Conversation history

## Purpose

Let a follow-up question use the earlier messages of the same chat. Open WebUI already sends the messages for the active chat with each request. This story passes a small, recent slice of them into the existing prompt so the Learning Companion can answer "and what about that?" style questions.

## What this story implements in plain English

- You can ask a first question, then ask a follow-up that only makes sense with the first one, and the chatbot understands it.
- The chatbot reads your earlier questions and its own earlier answers, in the order they happened, before it replies.
- It only looks at the most recent few messages of the current chat, not the whole conversation.
- It remembers nothing once the reply is done. A new chat, or a restart, starts fresh.
- Open WebUI looks and works exactly as before, including streaming.

## Prerequisites

- Stories 1.1 and 2.1 are done. The app has the three routes, the prompt template in `src/learning_companion/chain.py`, and the working Open WebUI connection.
- The provider is **Gemini** (`GEMINI_API_KEY`, `GEMINI_MODEL_NAME` in `.env`). Stories 1.1 and 2.1 were first written for Grok and the project was switched to Gemini. Keep the current Gemini settings and package unchanged.
- Read first: `docs/config.yaml` (if present), `docs/architecture.md`, Stories 1.1 and 2.1, `.env.example`, `src/learning_companion/chain.py`, `main.py` and `config.py`.
- Preserve the working endpoints, settings, LangChain prompt template, normal JSON and SSE behaviour, and the Open WebUI connection. No new dependencies are expected.

## Work to do

1. In `src/learning_companion/chain.py`, add a LangChain `MessagesPlaceholder` (named `history`) to the existing prompt so the order is: application system instruction → `history` → current human message. Do not assemble history into an ad-hoc string.
2. In `src/learning_companion/main.py`, build the history from the request:
   - The current message is still the latest `user` message.
   - History is the supported messages that come **before** it, kept in their original order. Only `user` and `assistant` messages count.
   - Convert them to LangChain `HumanMessage` and `AIMessage` objects.
   - Keep only the most recent `MAX_HISTORY_MESSAGES` of them. Define it as one named constant, `10`, with a comment explaining the limit.
   - Safely skip anything unsupported: any `system` message (it must never replace or be added to the application's stable instruction), empty content, or unknown roles.
3. Keep the same prompt → Gemini model → text-output chain for both the normal and the streaming paths. Keep request and response shapes, routes and the configuration error unchanged.
4. Update the development-only log from Story 2.1 (only when `APP_ENV=development`) so it shows the message roles and the message count that reach the prompt, e.g. `roles=['system', 'human', 'ai', 'human'] count=4`. Never log API keys, the full system instruction or large message bodies.
5. Nothing is saved. No files, no database, no cache, no cross-session memory.
6. Update `docs/architecture.md` with:
   - the request-provided history flow: Open WebUI request → recent `user`/`assistant` messages (up to the limit) → `[system instruction, history, latest user message]` → Gemini → answer;
   - the message limit (10);
   - the no-persistence boundary.
7. Do not add a database, persistent memory, RAG, tools, MCP, routing, LangGraph, a new endpoint, a new UI, an evaluation harness or a broad test suite.

## Completion checks

Run only these and report the commands you actually ran:

```
uv run ruff format .
uv run ruff check .
uv run uvicorn learning_companion.main:app --host 127.0.0.1 --port 8000
```

Then, in a **new** Open WebUI chat with the Gemini model (restart the API after any `.env` change):

- [ ] Send: "My favourite topic is Python lists. Please remember that." A short friendly reply appears.
- [ ] Send the follow-up: "What did I say my favourite topic was?" The answer mentions Python lists.
- [ ] The development log for the follow-up shows the role sequence `system, human, ai, human` with `count=4`. No key, full instruction or full message text is logged.
- [ ] Start another new chat and ask the same follow-up. The chatbot does not know the earlier topic.
- [ ] `/health`, `/v1/models`, streaming replies and the Open WebUI connection work as before.
- [ ] `docs/architecture.md` shows the history flow, the limit and the no-persistence boundary.

Expected two-turn Open WebUI result: the first reply acknowledges the topic, and the second reply correctly says "Python lists". In a fresh chat, the topic is forgotten.

## Handover

Files this story changes:

- `src/learning_companion/chain.py` (history placeholder in the prompt)
- `src/learning_companion/main.py` (history building, limit constant, log line)
- `docs/architecture.md` (history flow, limit, no-persistence boundary)

Story 3.1 will extend this working chatbot. The routes, settings, prompt template, history handling and Open WebUI connection stay as they are.
