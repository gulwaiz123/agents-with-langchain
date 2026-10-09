import json
import time
import uuid
from typing import Literal

from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from pydantic import BaseModel

from learning_companion.chain import (
    PROMPT,
    STUDY_HELPER_PROMPT,
    ConfigurationError,
    build_chain,
    build_study_helper_chain,
)
from learning_companion.config import get_settings
from learning_companion.dev_log import log_request, log_response
from learning_companion.routing import STUDY, choose_route

app = FastAPI(title="Learning Companion")


class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    model: str
    messages: list[Message]
    stream: bool = False


STUDY_NEEDS_QUESTION = (
    "What would you like to study? Try `/study Explain what an API is`."
)

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
    route, question = choose_route(question)
    label = f"[route: {route}]\n\n"

    # "/study" with nothing after it: ask for a topic instead of calling the model.
    chain = None
    if route == STUDY and not question:
        prompt = STUDY_HELPER_PROMPT
    else:
        try:
            if route == STUDY:  # the visible if/else: pick the chain
                chain, prompt = (
                    build_study_helper_chain(get_settings()),
                    STUDY_HELPER_PROMPT,
                )
            else:
                chain, prompt = build_chain(get_settings()), PROMPT
        except ConfigurationError as error:
            return JSONResponse(
                status_code=500,
                content={
                    "error": {"message": str(error), "type": "configuration_error"}
                },
            )

    inputs = {"history": history, "question": question}
    completion_id = f"chatcmpl-{uuid.uuid4().hex}"
    dev = get_settings().app_env == "development"
    if dev:
        log_request(
            completion_id,
            request.model_dump(),
            prompt.format_messages(**inputs),
            len(history),
            route,
        )
    started = time.perf_counter()

    def pieces():
        yield label
        if chain is None:
            yield STUDY_NEEDS_QUESTION
        else:
            yield from (
                chain.stream(inputs) if request.stream else [chain.invoke(inputs)]
            )

    if not request.stream:
        answer = "".join(pieces())
        if dev:
            log_response(completion_id, answer, time.perf_counter() - started, False)
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
        parts = []
        for text in pieces():
            if text:
                parts.append(text)
                yield _chunk(completion_id, request.model, {"content": text}, None)
        if dev:
            log_response(
                completion_id, "".join(parts), time.perf_counter() - started, True
            )
        yield _chunk(completion_id, request.model, {}, "stop")
        yield "data: [DONE]\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")
