# Story 3.2 — Visible Python routing

## Purpose

Make the two existing chains, general chat and study helper, reachable from the same Open WebUI chat. A plain Python `if/else` picks the chain, so participants can read exactly how the choice is made. Session 4 will later replace this internally with an explicit LangGraph route.

## What this story implements in plain English

- An ordinary message, such as "Hello!", is answered by general chat exactly as before.
- A message that starts with `/study`, such as `/study Explain what an API is`, is answered by the study helper.
- The study helper answers the question without the `/study` word, with a plain explanation and one next step.
- Both kinds of message use the same Open WebUI chat, and earlier messages in the chat still count as context.
- You can see which path was taken, in the server log and in a short label at the start of the reply.

## Prerequisites

- Stories 1.1 to 3.1 are done. The app has the three routes, the general-chat chain (`build_chain`), the study-helper chain (`build_study_helper_chain`), request-provided history (Story 2.2), the development log in `src/learning_companion/dev_log.py`, and the working Open WebUI connection.
- The provider is **Gemini** (`GEMINI_API_KEY`, `GEMINI_MODEL_NAME` in `.env`). Earlier stories were first written for Grok and the project was switched to Gemini. Keep the current Gemini settings and package unchanged.
- Read first: `docs/config.yaml` (if present), `docs/architecture.md`, Stories 1.1 to 3.1, `.env.example`, `src/learning_companion/chain.py`, `main.py`, `dev_log.py` and `config.py`.
- Preserve the working Open WebUI connection, endpoints, settings, message-history handling and the normal JSON and SSE response shapes.

## Work to do

1. In `src/learning_companion/main.py` (or a tiny `routing.py` if clearer), add one deliberately simple, visible rule as ordinary Python:
   - If the latest user message begins with `/study`, select the study-helper chain.
   - Otherwise select the existing general-chat chain.
   Keep it a readable `if/else`. No classification by the model, no scoring, no registry of routes.
2. Strip only the leading `/study` marker (and the whitespace right after it) from the current question before it goes to the study helper. Leave the rest of the text unchanged. A message of only `/study` becomes an empty question; return a short friendly general reply asking what to study rather than calling the model with an empty question. Messages that merely contain `/study` later in the text, or are written like `/studying`, use general chat.
3. Keep all other current request messages as history under the Story 2.2 rules (earlier `user` and `assistant` messages only, up to `MAX_HISTORY_MESSAGES`, request `system` messages never replace the application's instruction). Both chains receive the same history.
4. Use the selected chain through the existing normal and streaming response adapter. Do not change the request shape, response shape, routes or the configuration error. Build only the chain that was selected.
5. Record the selected route, `general` or `study`, in the development log (only when `APP_ENV=development`). Add one `route : general` or `route : study` line to the request block in `dev_log.py`. Never log API keys or settings.
6. Add a short, classroom-readable route label at the start of the answer text, for example `[route: general]` or `[route: study]`, followed by a blank line and the model's answer. It is part of the normal answer text only. For streaming, send it as the first text chunk. Do not add custom response fields, custom events or Open WebUI plugins.
7. Update `docs/architecture.md` with:
   - the `/study` rule and the selected-chain path: Open WebUI request → read latest user message → `if` starts with `/study` then study helper, `else` general chat → selected chain → text answer (with route label);
   - the boundary: this is deterministic application routing, not LLM classification, LangGraph or multi-agent orchestration.
8. Do not add LLM routing, more specialists, review steps, loops, a new endpoint or UI, a database, retrieval, tools, MCP, LangGraph, broad tests or production controls.

## Completion checks

Run only these and report the commands you actually ran:

```
uv run ruff format .
uv run ruff check .
uv run uvicorn learning_companion.main:app --host 127.0.0.1 --port 8000
```

Then, in the existing Open WebUI chat with the Gemini model (restart the API after code or `.env` changes):

- [ ] Send "Hello!". The reply starts with `[route: general]` and is a normal friendly answer.
- [ ] Send `/study Explain what an API is`. The reply starts with `[route: study]`, then gives a clear plain explanation and exactly one next step.
- [ ] The server log shows `route : general` for the first request and `route : study` for the second, and the study request's messages sent to the model do not contain the `/study` marker.
- [ ] Both replies came through the same `POST /v1/chat/completions` endpoint and the same Open WebUI conversation.
- [ ] `/health`, `/v1/models`, streaming and the Open WebUI connection work as before.
- [ ] `docs/architecture.md` shows the `/study` rule and the not-LangGraph boundary.

Expected Open WebUI results:
- General: `[route: general]` followed by a friendly general-chat reply.
- Study: `[route: study]` followed by a plain-language explanation of an API and one suggested next learning step.

## Handover

Files this story changes:

- `src/learning_companion/main.py` (the `/study` rule and chain selection; optional small `routing.py`)
- `src/learning_companion/dev_log.py` (route line in the request block)
- `docs/architecture.md` (`/study` rule, selected-chain path, boundary)

Story 4.1 will extend this by replacing the Python `if/else` with an explicit LangGraph route inside the app. The visible behaviour (`/study` versus ordinary messages, same endpoint, same Open WebUI chat) stays as it is.
