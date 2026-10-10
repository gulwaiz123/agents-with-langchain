import json
import re
import time
import uuid
from typing import Literal

from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from pydantic import BaseModel

from learning_companion.chain import PROMPT, STUDY_HELPER_PROMPT, ConfigurationError
from learning_companion.config import get_settings
from learning_companion.dev_log import log_request, log_response
from learning_companion.graph import run_graph
from learning_companion.routing import STUDY

app = FastAPI(title="Learning Companion")


class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    model: str
    messages: list[Message]
    stream: bool = False


# Only this many recent earlier messages from the current request are used.
# Nothing is stored: history exists only for the length of one request.
MAX_HISTORY_MESSAGES = 10


def _split_request(messages: list[Message]) -> tuple[list[BaseMessage], str]:
    """Return (recent history, latest user message).

    History is the earlier supported `user`/`assistant` messages in their
    original order. `system` messages and empty content are skipped, so a
    client can never replace the application's instruction.
    """
    supported = [m for m in messages if m.role in ("user", "assistant") and m.content]
    last_user = next(
        (i for i in range(len(supported) - 1, -1, -1) if supported[i].role == "user"),
        None,
    )
    if last_user is None:
        return [], ""
    history = [
        HumanMessage(content=m.content)
        if m.role == "user"
        else AIMessage(content=m.content)
        for m in supported[:last_user]
    ]
    return history[-MAX_HISTORY_MESSAGES:], supported[last_user].content


def _chunk(completion_id: str, model: str, delta: dict, finish: str | None) -> str:
    payload = {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
    }
    return f"data: {json.dumps(payload)}\n\n"


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/v1/models")
def list_models():
    name = get_settings().gemini_model_name
    data = (
        [{"id": name, "object": "model", "created": 0, "owned_by": "google"}]
        if name
        else []
    )
    return {"object": "list", "data": data}


@app.post("/v1/chat/completions")
def chat_completions(request: ChatRequest):
    history, question = _split_request(request.messages)
    started = time.perf_counter()
    try:
        state, nodes = run_graph(history, question)
    except ConfigurationError as error:
        return JSONResponse(
            status_code=500,
            content={"error": {"message": str(error), "type": "configuration_error"}},
        )

    route = state["route"]
    answer = f"[route: {route}]\n\n{state['final_answer']}"
    completion_id = f"chatcmpl-{uuid.uuid4().hex}"
    if get_settings().app_env == "development":
        prompt = STUDY_HELPER_PROMPT if route == STUDY else PROMPT
        log_request(
            completion_id,
            request.model_dump(),
            prompt.format_messages(history=history, question=state["user_message"]),
            len(history),
            route,
            nodes,
            {
                "decision": state["review_decision"],
                "reason": state["review_reason"],
                "revisions": state["revision_count"],
            },
        )
        log_response(
            completion_id, answer, time.perf_counter() - started, request.stream
        )

    if not request.stream:
        return {
            "id": completion_id,
            "object": "chat.completion",
            "created": int(time.time()),
            "model": request.model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": answer},
                    "finish_reason": "stop",
                }
            ],
        }

    def events():
        yield _chunk(completion_id, request.model, {"role": "assistant"}, None)
        # The graph returns the finished answer; send it as small text chunks.
        for text in re.findall(r"\S+\s*|\s+", answer):
            yield _chunk(completion_id, request.model, {"content": text}, None)
        yield _chunk(completion_id, request.model, {}, "stop")
        yield "data: [DONE]\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")
