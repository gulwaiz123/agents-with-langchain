# Learning Companion Chatbot

A small local app for the LangChain classroom course. Open WebUI (already installed and working) sends chat messages to this app, which answers with one LangChain prompt and a Gemini model.

Flow: `Open WebUI → this app's /v1/chat/completions → LangChain prompt + Gemini → answer in Open WebUI`

See [docs/architecture.md](docs/architecture.md).

## Run it

```
uv sync
copy .env.example .env      # Windows (use cp on macOS/Linux)
uv run uvicorn learning_companion.main:app --host 127.0.0.1 --port 8000
```

Edit `.env`:

- `GEMINI_MODEL_NAME` — supplied by your instructor.
- `GEMINI_API_KEY` — your real key. Put it only in the untracked `.env`, never in `.env.example`.

The app starts without a key. If you send a chat message before setting the key and model name, you get a clear configuration error.

## Check it

```
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/v1/models
```

## Open WebUI connection value

Open WebUI itself is not changed. If its existing connection needs pointing at this app, the only value to use is the base URL `http://127.0.0.1:8000/v1` (or `http://host.docker.internal:8000/v1` if Open WebUI runs in Docker). Then select the Gemini model name your instructor gave you.

## Lint

```
uv run ruff format .
uv run ruff check .
```
