import json
import time
import uuid
from typing import Literal

from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from learning_companion.chain import ConfigurationError, build_chain
from learning_companion.config import get_settings

app = FastAPI(title="Learning Companion")


class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    model: str
    messages: list[Message]
    stream: bool = False


def _latest_user_message(messages: list[Message]) -> str:
    for message in reversed(messages):
        if message.role == "user":
            return message.content
    return ""


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
    try:
        chain = build_chain(get_settings())
    except ConfigurationError as error:
        return JSONResponse(
            status_code=500,
            content={"error": {"message": str(error), "type": "configuration_error"}},
        )

    question = _latest_user_message(request.messages)
    completion_id = f"chatcmpl-{uuid.uuid4().hex}"

    if not request.stream:
        answer = chain.invoke({"question": question})
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
        for text in chain.stream({"question": question}):
            if text:
                yield _chunk(completion_id, request.model, {"content": text}, None)
        yield _chunk(completion_id, request.model, {}, "stop")
        yield "data: [DONE]\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")
