# Story 3.1 — Study-helper chain

## Purpose

Give the Learning Companion a second way of answering: a study helper that explains a beginner technical idea in plain language and ends with one small next step. This story builds that ability only. Choosing when to use it comes in Story 3.2.

## What this story implements in plain English

- The chatbot still answers greetings and ordinary chat exactly as before in Open WebUI.
- A study-helper answer is now available for developers to try locally: a short, plain explanation of a beginner technical idea.
- That answer includes a small example when one helps.
- It always ends with one suggested next learning step.
- The study helper is honest about its limits. It does not search, browse, look up course material or promise to be correct.

## Prerequisites

- Stories 1.1, 2.1 and 2.2 are done. The app has the three routes, the prompt template with history in `src/learning_companion/chain.py`, and the working Open WebUI connection.
- The provider is **Gemini** (`GEMINI_API_KEY`, `GEMINI_MODEL_NAME` in `.env`). Earlier stories were first written for Grok and the project was switched to Gemini. Keep the current Gemini settings and package unchanged.
- Read first: `docs/config.yaml` (if present), `docs/architecture.md`, Stories 1.1 to 2.2, `.env.example`, and `src/learning_companion/chain.py`, `main.py` and `config.py`.
- Preserve the existing endpoints, settings, request and response behaviour, Open WebUI connection and conversation-message handling.

## Work to do

1. In `src/learning_companion/chain.py`, keep the existing general-chat chain and its instruction untouched. Do not rename or change it.
2. Add a separately named study-helper chain in the same file, built the same way: prompt → Gemini model → text output.
   - Give it its own named instruction constant, e.g. `STUDY_HELPER_INSTRUCTION`, kept as the application-owned system message. User content stays separate from it.
   - The instruction asks for: a concise plain-language explanation, a small example where useful, and exactly one suggested next learning step.
   - The instruction must not claim research, browsing, retrieval of course data, or guaranteed correctness.
   - Reuse the same prompt structure (system instruction → `history` placeholder → current message), the same configured Gemini model and the same missing-setting configuration error. Share the model setup between both chains rather than duplicating it.
3. Do not change the active route. `POST /v1/chat/completions` must keep using the general-chat chain for every request. Do not add `/study` or any other selection logic; Story 3.2 does that. No new endpoint.
4. Add a small project-local way to invoke the study-helper chain during development, for example `src/learning_companion/try_study_helper.py`, run with `uv run python -m learning_companion.try_study_helper "What is a variable?"`. It reads the question from the command line, uses the same settings, prints the answer, and exits with the clear configuration message if the key or model name is missing. It must not touch the Open WebUI endpoint.
5. Update `docs/architecture.md` with the two chain behaviours and what each is responsible for:
   - general chat: greetings and ordinary conversation (the only one the endpoint uses now);
   - study helper: beginner technical explanation plus one next step (available, not yet selected).
   State clearly that this story creates the study-helper capability only and that choosing between chains is the next story.
6. Do not add routing, LLM-based classification, more specialists, loops, review steps, a second application, endpoint, provider, UI, database, retrieval, MCP server, tool call, LangGraph workflow, autonomous agent, broad tests or production controls.

## Completion checks

Run only these and report the commands you actually ran:

```
uv run ruff format .
uv run ruff check .
uv run uvicorn learning_companion.main:app --host 127.0.0.1 --port 8000
uv run python -m learning_companion.try_study_helper "What is a variable?"
```

- [ ] Ruff format and check pass.
- [ ] In the existing Open WebUI chat, send one ordinary message (for example "Hello!"). The reply is a normal general-chat answer, unchanged from before.
- [ ] The local study-helper command prints a plain explanation, a small example if useful, and exactly one next step. It makes no claim to browse, research or look up course data.
- [ ] `docs/architecture.md` lists both chain behaviours and says selection is Story 3.2.
- [ ] `/health`, `/v1/models`, streaming and the Open WebUI connection work as before.

Expected result: Open WebUI general chat is unchanged. The local study-helper run returns a short explanation of "a variable" ending with one next step.

## Handover

Files this story changes or adds:

- `src/learning_companion/chain.py` (study-helper instruction and chain; general chat untouched)
- `src/learning_companion/try_study_helper.py` (new, development-only helper)
- `docs/architecture.md` (two chain behaviours)

Story 3.2 will extend this by adding the visible `/study` route rule so Open WebUI messages can choose the study-helper chain. The endpoint, settings, history handling and Open WebUI connection stay as they are.
