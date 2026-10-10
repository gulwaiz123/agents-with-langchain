# Story 4.2 — Bounded review and improve

## Purpose

Extend the routing graph from Story 4.1 so the chatbot checks its own draft answer once, improves it once only when needed, and then stops. This adds a small, visible review cycle without turning the chatbot into an open-ended agent.

## What this story implements in plain English

- After the chatbot writes a first answer, a second step checks it against a short, fixed set of classroom rules.
- If the draft is clear and suitable, it is sent to Open WebUI as it is.
- If the draft is not good enough, a third step rewrites it once, using the reason given by the checker.
- The rewritten answer is checked one last time and then sent, whatever the result. The chatbot never improves more than once.
- The server log shows the route, the checker's decision and reason, how many rewrites happened, and the steps that ran.

## Prerequisites

- Stories 1.1 to 4.1 are done. The app has the graph in `src/learning_companion/graph.py` (state, `router`, `general_chat`, `study_helper`), the two answer chains in `chain.py`, request-provided history (Story 2.2), the development log in `dev_log.py`, and the working Open WebUI connection.
- The provider is **Gemini** (`GEMINI_API_KEY`, `GEMINI_MODEL_NAME` in `.env`). Earlier stories were first written for Grok and the project was switched to Gemini. Keep the current Gemini settings and package unchanged.
- Read first: `docs/config.yaml` (if present), `docs/architecture.md`, Stories 1.1 to 4.1, `.env.example`, and `graph.py`, `chain.py`, `main.py`, `dev_log.py`.
- Preserve the Open WebUI connection, endpoints, request and response shape, settings, normal JSON replies, streaming SSE behaviour and the Story 4.1 routing path. No new dependencies are expected.

## Work to do

### Words used in this story

- The **reviewer** and **improver** are small LLM-powered specialist nodes. For this classroom example they may be called specialist agents.
- The **router** is still ordinary Python logic, not an agent.
- There is still no MCP tool call. An MCP call could be a future node and is outside this story.

### The new state fields, in plain English

Add exactly these five fields to the graph state from Story 4.1, and nothing else:

| Field | Plain-English meaning |
|---|---|
| `draft_answer` | The answer as currently written. The answer nodes write it first; the improver replaces it with the rewrite. |
| `review_decision` | The checker's verdict on the current draft: `approve` or `improve`. |
| `review_reason` | One short sentence from the checker saying why. |
| `revision_count` | How many rewrites have happened. Starts at 0 and never goes above 1. |
| `final_answer` | The reply to send to Open WebUI. Written only when the workflow is finishing. |

The Story 4.1 `answer` field is replaced by `draft_answer` and `final_answer`. The other four fields (`user_message`, `messages`, `route`) stay.

### Steps

1. In `src/learning_companion/graph.py`, change `general_chat` and `study_helper` so they write `draft_answer` instead of a final answer. Keep their prompts, chains, the bare `/study` behaviour and the configuration error unchanged. The bare `/study` reply is a fixed message with no model call; it skips review and is written straight to `final_answer`.
2. Add the **answer-reviewer node** (`reviewer`):
   - Input: `draft_answer`, `route` and the user's question.
   - It judges the draft against one short fixed classroom rule kept as a named constant, for example: the answer must be plain-English and easy for a beginner, match the role (general chat is friendly and brief; study help gives an explanation and exactly one next step), and not claim to browse, research or look things up.
   - It returns a structured result: `decision` (`approve` or `improve`) and one short `reason`. Use LangChain structured output with a small Pydantic model, so the decision is one of the two allowed words.
   - It writes `review_decision` and `review_reason`.
   - Bound: if `revision_count` is 1, it does not call the model again. It sets `review_decision` to `approve` with a reason such as "revision limit reached; accepting the current draft", and writes `final_answer` from `draft_answer`. When it approves for any reason, it writes `final_answer` from `draft_answer`.
3. Add the **answer-improver node** (`improver`):
   - Input: `draft_answer`, `review_reason` and the user's question.
   - It rewrites the answer once, keeping the same role and format rules, and writes the new `draft_answer`.
   - It increments `revision_count` by 1.
   - It uses no tools, no browsing, no retrieval, no planning and makes no routing choice.
4. Wire these bounded edges, all visible in code:
   - `START → router` and the conditional router edges from Story 4.1 stay.
   - `general_chat → reviewer` and `study_helper → reviewer`.
   - Conditional from `reviewer`: `approve` goes to `END`; `improve` goes to `improver` only when `revision_count` is 0.
   - `improver → reviewer`, for one final approval.
   This is the one visible cycle (reviewer → improver → reviewer) with a maximum of one improvement. There is no other loop, retry, planner, tool or open-ended agent behaviour.
5. Keep using the same configured Gemini model for the reviewer and improver. Missing settings still produce the existing configuration error. Do not change prompts or settings of the answer chains.
6. In `src/learning_companion/main.py`, send `final_answer` through the existing normal and streaming adapters exactly as Story 4.1 does (with the `[route: ...]` label). No custom response fields, custom Open WebUI events or plugins.
7. Extend the development-only log in `dev_log.py` (only when `APP_ENV=development`) with compact lines for the route, the review decision and reason, the revision count and the node sequence, for example `review : improve (too long for a beginner)`, `revisions : 1`, `nodes : router -> study_helper -> reviewer -> improver -> reviewer`. Never log API keys, full hidden prompts or settings.
8. Update `docs/architecture.md` with: the two new nodes, the five new state fields, the full graph diagram, the edge rules, the one-revision limit and the scope boundary.
9. Do not add databases, persistence, RAG, web search, tools, MCP, human approval, additional agents, broad test suites, production controls, observability platforms or deployment work.

## Completion checks

Run only these and report the commands you actually ran:

```
uv run ruff format .
uv run ruff check .
uv run uvicorn learning_companion.main:app --host 127.0.0.1 --port 8000
```

Then, in the existing Open WebUI chat with the Gemini model (restart the API after code or `.env` changes):

- [ ] Send "Hello!". The reviewer approves the draft directly. The reply starts with `[route: general]`. Trace: `nodes : router -> general_chat -> reviewer`, `review : approve`, `revisions : 0`.
- [ ] Send a `/study` question chosen to benefit from clearer wording, for example `/study Explain what polymorphism is in object-oriented programming, with every technical term`. Inspect the review path. If the reviewer approves the first draft, try one more question. The expected trace is `nodes : router -> study_helper -> reviewer -> improver -> reviewer`, with `review : improve` first and `revisions : 1`.
- [ ] The final answer appears in Open WebUI starting with `[route: study]`, with a plain explanation and one next step.
- [ ] No more than one improvement ever happens: `revisions` is never above 1 in the log.
- [ ] `/health`, `/v1/models`, streaming and the Open WebUI connection work as before.
- [ ] `docs/architecture.md` shows the full graph, new state fields, edge rules and the one-revision limit.

Expected Open WebUI results:
- Ordinary question: `[route: general]` and a friendly reply, approved on the first check.
- Study question: `[route: study]` and the improved, clearer explanation with one next step.

## Handover

Files this story changes:

- `src/learning_companion/graph.py` (new state fields, `reviewer` and `improver` nodes, bounded edges)
- `src/learning_companion/main.py` (sends `final_answer` through the adapters)
- `src/learning_companion/dev_log.py` (review decision, revision count, node sequence)
- `docs/architecture.md` (new nodes, state, full graph, limit, scope)

Final capstone outcome: a small Learning Companion Chatbot in Open WebUI. It remembers recent messages of the current chat, answers ordinary questions in general-chat style, answers `/study` questions as a study helper, and checks every drafted answer once, improving it at most once, using a LangGraph workflow with a plain-Python router and two LLM specialist nodes. There is no persistence, no tools and no MCP. This is the end of the course stories.
