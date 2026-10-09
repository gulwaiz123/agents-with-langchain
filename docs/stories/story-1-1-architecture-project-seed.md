# Story 1.1 — Architecture and project seed

## Purpose

Agree the architecture for the **Learning Companion Chatbot** with the instructor, then seed a small Python project. The project answers chat messages from the Open WebUI that participants already use, with one reply from Gemini.

This is the first story in a short, beginner LangChain and LangGraph classroom course. Keep everything small.

## What this story implements in plain English

After this story, a participant will be able to:

- Read a one-page plan showing how a chat message travels from Open WebUI to Gemini and back.
- Start a small local app with one command, even before adding a real key.
- Put their own key and the instructor's model name in a private `.env` file.
- Pick the Gemini model in Open WebUI, send a message, and see one reply.
- Watch the same reply appear word by word when streaming is on.

## Prerequisites

- Open WebUI is already installed and working. It is the supplied chat client only. Do not reinstall, reconfigure, modify or build it.
- Python 3.12 and `uv` are installed.
- The instructor will supply the Gemini model name. The participant has their own Gemini API key.
- Repository root is the project path. `docs/config.yaml` does not exist and `docs/architecture.md` does not exist yet. Re-check both before starting. If a config sets a project path, use it. If the architecture file now exists, update it instead of replacing it.
- Existing work (`README.md`, `docs/`) must be preserved. `README.md` is currently empty and may be filled in.

## Work to do

### Part A — Architecture (do this first, then stop)

1. Create or update `docs/architecture.md`. Keep it to about one page. It must record:
   - The single classroom flow:
     `Open WebUI → this local application’s OpenAI-compatible chat endpoint → LangChain prompt and Gemini model → answer in Open WebUI`.
   - Open WebUI is already installed and working. It is the supplied chat client only and is never reinstalled, reconfigured, modified or built by participants.
   - The capstone is a small **Learning Companion Chatbot**. It is not a custom frontend and not a second demonstration application.
   - Light boundaries:
     - API keys stay in an untracked `.env`.
     - Application instructions stay separate from user messages.
     - Out of scope for this course: authentication, authorization, security hardening, databases, persistent memory, RAG, production deployment and extensive tests.
   - Planned endpoints: `GET /health`, `GET /v1/models`, `POST /v1/chat/completions`.
   - Planned stack: Python 3.12, UV, FastAPI, Uvicorn, Pydantic settings, `langchain`, the Gemini LangChain provider integration (`langchain-google-genai`), Ruff, and a minimal test runner.
   - The setting names listed in Part B.
2. **Stop and ask the instructor to approve `docs/architecture.md`.**
   - Before approval, do not create seed files, install dependencies or scaffold code.
   - Resume this same story only after the instructor explicitly approves. If they ask for changes, edit the architecture and ask again.

### Part B — Project seed (only after approval)

1. Set up the project with UV on Python 3.12. Add runtime dependencies: FastAPI, Uvicorn, Pydantic settings, `langchain`, and the Gemini LangChain provider integration (`langchain-google-genai`). Add dev dependencies: Ruff and a minimal test runner (pytest). Confirm the current package name for the Gemini-compatible integration (`langchain-google-genai`) before adding it.
2. Create `.env.example` with exactly these settings:

   ```
   APP_ENV=development
   GEMINI_API_KEY=
      GEMINI_MODEL_NAME=
   HOST=127.0.0.1
   PORT=8000
   ```

   Add no Claude, alternate-provider, database or production settings.
3. Create `.gitignore` so `.env`, `.venv/`, caches and build output are untracked. `.env.example` stays tracked.
4. Create the `src/learning_companion/` package. Keep it small, for example:
   - `config.py`: Pydantic settings that read the names above. Missing key or model name must not stop startup.
   - `chain.py`: one LangChain flow of prompt → Gemini chat model → text output. The prompt has a fixed Learning Companion instruction as the system message and the latest user message as the human message. Nothing else.
   - `main.py`: the FastAPI app and the three routes.
5. Implement the routes:
   - `GET /health` returns a simple OK response.
   - `GET /v1/models` returns an OpenAI-compatible model list containing the configured Gemini model, so Open WebUI can select it. If no model name is set, return an empty list.
   - `POST /v1/chat/completions` accepts `model`, `messages` (text only; roles `system`, `user` or `assistant`) and `stream`.
     - `stream` false: return normal OpenAI-compatible chat-completion JSON.
     - `stream` true: return text-only OpenAI-compatible SSE chunks, then a stop chunk, then `data: [DONE]`.
     - Both paths use the same single flow from `chain.py` and only the latest user message. Do not use the rest of the history yet.
     - If the key or model name is missing, return an honest configuration error (a clear message saying which setting is missing) only when the model call is attempted. The app must start and `/health` must work without a real key.
   - Do not add custom Open WebUI events, a second chat route or a custom browser UI.
6. Create `tests/` with at most one tiny test, for example `/health` returns OK. Do not write a broad test suite.
7. Write `README.md` with: what the app is, how to run `uv sync`, copy `.env.example` to `.env`, and start the server. State that the instructor supplies the model name, and that participants put their real key only in untracked `.env`. If Open WebUI’s existing connection needs a different local base URL or model selection, document only that application-side value (for example the base URL `http://127.0.0.1:8000/v1`, or `http://host.docker.internal:8000/v1` if Open WebUI runs in Docker) and which model to pick. Do not describe changes to Open WebUI itself.
8. Do not add tool calls, LangGraph, agents, MCP, or advanced streaming features.

## Completion checks

Run only these lightweight checks and report the commands you actually ran:

```
uv sync
uv run ruff format .
uv run ruff check .
uv run uvicorn learning_companion.main:app --host 127.0.0.1 --port 8000
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/v1/models
```

Then, using the existing Open WebUI setup (with the key and model name in `.env`):

- [ ] Ruff format and check pass.
- [ ] The API starts with an empty `GEMINI_API_KEY`, and `/health` returns OK.
- [ ] `/v1/models` lists the configured Gemini model.
- [ ] One normal (non-streaming) request through Open WebUI shows one Gemini reply.
- [ ] One streaming request through Open WebUI shows one Gemini reply appearing as text.
- [ ] `.env` is not tracked by git; `.env.example` is.
- [ ] `docs/architecture.md` was approved by the instructor before any seed file existed.

If Open WebUI cannot reach the app, adjust only the connection base URL or model selection, as documented in `README.md`. Do not change Open WebUI.

Expected classroom result: one Gemini reply visible in Open WebUI.

## Handover

Files created or changed by this story:

- `docs/architecture.md` (Part A, before approval)
- `pyproject.toml`, `uv.lock`
- `.env.example`, `.gitignore`, `README.md`
- `src/learning_companion/` (`__init__.py`, `config.py`, `chain.py`, `main.py`)
- `tests/` (one tiny health test at most)

Story 2.1 will extend this seed by building the full prompt and using conversation history. This story deliberately uses only a fixed instruction and the latest user message. The endpoint, settings and Open WebUI connection stay as they are.
