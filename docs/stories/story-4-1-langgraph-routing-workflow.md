# Story 4.1 — LangGraph routing workflow

## Purpose

Replace the plain Python `if/else` from Story 3.2 with one small LangGraph workflow, so the route, the state and the steps are visible as a graph. What participants see in Open WebUI does not change. Only the inside of the app does.

## What this story implements in plain English

- A question enters the chatbot and is written down in a small shared "notebook" that every step can read and add to.
- The first step looks at the message and decides: ordinary chat, or study help (a message starting with `/study`).
- Exactly one of two answering steps then runs: general chat or study helper. Each writes its answer in the notebook.
- The answer is sent back to Open WebUI as before, with the same `[route: ...]` label.
- The server log shows the route and the steps that ran, for example `router -> study_helper`.

## Prerequisites

- Stories 1.1 to 3.2 are done. The app has the three routes, `build_chain` and `build_study_helper_chain` in `src/learning_companion/chain.py`, `choose_route` in `src/learning_companion/routing.py`, request-provided history (Story 2.2), the development log in `dev_log.py`, and the working Open WebUI connection.
- The provider is **Gemini** (`GEMINI_API_KEY`, `GEMINI_MODEL_NAME` in `.env`). Earlier stories were first written for Grok and the project was switched to Gemini. Keep the current Gemini settings and package unchanged.
- Read first: `docs/config.yaml` (if present), `docs/architecture.md`, Stories 1.1 to 3.2, `.env.example`, and `chain.py`, `routing.py`, `main.py`, `dev_log.py`.
- Preserve the Open WebUI connection, endpoints, request and response shape, settings, normal JSON replies and streaming SSE behaviour.
- The only new dependency is `langgraph` (add it with `uv add langgraph`).

## Work to do

### Words used in this story

- A **node** is a focused piece of work in the workflow. A node is not automatically an agent.
- The **router** is ordinary application logic, not an agent and not a model call.
- The two answering nodes call Gemini through the existing chains. They can be called small specialist behaviours.
- An MCP tool call could sit inside a future node. MCP is **not** implemented in this course story.

### The graph state, in plain English

The state is the shared notebook that travels through the graph. It has four fields:

| Field | Plain-English meaning |
|---|---|
| `user_message` | What the participant just asked, with any `/study` marker already handled by the router. |
| `messages` | The earlier chat messages from this request (Story 2.2 history), as LangChain messages. |
| `route` | The decision: `general` or `study`. Empty until the router has run. |
| `answer` | The final reply text. Empty until an answering node has run. |

Define it as a small typed state (`TypedDict`) with exactly these four fields.

### Steps

1. Add `langgraph` with `uv add langgraph`.
2. Create `src/learning_companion/graph.py` with one small LangGraph workflow, built with `StateGraph`:
   - **Router node** (`router`): ordinary Python. Reuses `choose_route` from `routing.py`, keeps the exact `/study` rule from Story 3.2, strips only the leading `/study` marker, and writes `general` or `study` plus the cleaned `user_message` into state.
   - **General-chat node** (`general_chat`): calls the existing general-chat chain with `messages` and `user_message`, and writes `answer`.
   - **Study-helper node** (`study_helper`): calls the existing study-helper chain the same way and writes `answer`. A `/study` message with no question keeps its Story 3.2 behaviour (the friendly "What would you like to study?" reply, no model call).
3. Wire these explicit edges, all visible in the code:
   - `START → router`
   - conditional edges from `router` to `general_chat` or `study_helper`, chosen by reading `route` from state
   - `general_chat → END`
   - `study_helper → END`
   There is no reviewer, improver, loop or retry. Story 4.2 adds the bounded review path.
4. Reuse the existing chains as they are. Do not change their prompts, the settings or the history conversion (`_split_request`, `MAX_HISTORY_MESSAGES`). Keep the missing-setting configuration error behaving as before.
5. In `src/learning_companion/main.py`, replace the inline `if/else` with a call to the compiled graph. The same single `POST /v1/chat/completions` route and the same normal and streaming adapters stay. The adapter takes the graph's final `answer`, prefixes the `[route: ...]` label as in Story 3.2, and returns it as normal JSON or as text-only SSE chunks ending with a stop chunk and `data: [DONE]`. Streaming may send the finished answer in small text chunks. Token-by-token streaming from inside the graph is not required.
6. Add a compact development-only trace (only when `APP_ENV=development`) reporting the route and the node sequence, for example `route : study` and `nodes : router -> study_helper`, by extending the request block in `dev_log.py`. Never log API keys, full hidden prompts or settings. Do not change the response format.
7. Update `docs/architecture.md` with: a graph diagram (router → general chat or study helper → end), the four state fields, each node's single responsibility, the edge rules, and what remains out of scope.
8. Do not add databases, persistence, RAG, web search, tool execution, MCP, human approval, review steps, loops, extra agents, broad test suites, security programmes, observability platforms, deployment work, a second application or a second chat route.

## Completion checks

Run only these and report the commands you actually ran:

```
uv add langgraph
uv run ruff format .
uv run ruff check .
uv run uvicorn learning_companion.main:app --host 127.0.0.1 --port 8000
```

Then, in the existing Open WebUI chat with the Gemini model (restart the API after code or `.env` changes):

- [ ] Send "Hello!". The reply starts with `[route: general]` and is a friendly general answer.
- [ ] Send `/study Explain what an API is`. The reply starts with `[route: study]`, then a plain explanation and exactly one next step.
- [ ] The server log shows `route : general` with `nodes : router -> general_chat`, and `route : study` with `nodes : router -> study_helper`.
- [ ] Both final answers appear in Open WebUI through the same endpoint, and streaming still works.
- [ ] `/health`, `/v1/models` and the Open WebUI connection work as before.
- [ ] `docs/architecture.md` shows the graph diagram, state fields, nodes, edges and out-of-scope list.

Expected results:
- General path: Open WebUI shows `[route: general]` and a friendly reply. Trace: `router -> general_chat`.
- Study path: Open WebUI shows `[route: study]`, a plain explanation and one next step. Trace: `router -> study_helper`.

## Handover

Files this story changes or adds:

- `pyproject.toml`, `uv.lock` (adds `langgraph`)
- `src/learning_companion/graph.py` (new: state, three nodes, edges)
- `src/learning_companion/main.py` (calls the graph instead of the inline `if/else`)
- `src/learning_companion/dev_log.py` (node sequence in the request block)
- `docs/architecture.md` (graph diagram, state, nodes, edges, out of scope)

Story 4.2 will extend this graph with a bounded review path. The routes, settings, chains, history handling and Open WebUI connection stay as they are.
