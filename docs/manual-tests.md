# Manual Tests

## Story 1.1 — Architecture and project seed

**What it adds:** a local API with `/health`, `/v1/models` and an OpenAI-compatible `/v1/chat/completions` that answers through one LangChain prompt and a Gemini model.

Prerequisite: set `GEMINI_API_KEY` and `GEMINI_MODEL_NAME` in `.env`, then start the API with `uv run uvicorn learning_companion.main:app --host 127.0.0.1 --port 8000`. Replace `YOUR_GEMINI_MODEL_NAME` below with the value of `GEMINI_MODEL_NAME`.

```bash
curl http://127.0.0.1:8000/health

curl http://127.0.0.1:8000/v1/models

curl -X POST http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "YOUR_GEMINI_MODEL_NAME", "messages": [{"role": "user", "content": "What is a variable?"}], "stream": false}'

curl -N -X POST http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "YOUR_GEMINI_MODEL_NAME", "messages": [{"role": "user", "content": "What is a variable?"}], "stream": true}'

curl -X POST http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "YOUR_GEMINI_MODEL_NAME", "messages": [{"role": "tool", "content": "hi"}]}'
```

Expected:
- `/health` returns `{"status":"ok"}`.
- `/v1/models` returns `"object":"list"` with one entry whose `id` is your `GEMINI_MODEL_NAME` (an empty `data` list if it is not set).
- The non-streaming chat returns a `chat.completion` JSON with `choices[0].message.content` holding a short plain-English answer and `finish_reason` `stop`.
- The streaming chat returns `chat.completion.chunk` events with text in `delta.content`, then a chunk with `finish_reason` `stop`, and ends with `data: [DONE]`.
- The last request uses an unsupported role, so it returns HTTP 422 validation error. If the key or model name is missing, any valid chat request instead returns HTTP 500 with `error.type` `configuration_error`.
