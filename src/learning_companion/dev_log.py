"""Development-only, human-readable request logging.

Shows the request payload, the messages sent to the model and the reply.
Never logs settings, so API keys cannot appear here.
"""

import json
import logging

from langchain_core.messages import BaseMessage

logger = logging.getLogger("uvicorn.error")

WIDTH = 72
MAX_TEXT = 2000  # long message bodies are cut so the console stays readable


def _clip(text: str) -> str:
    if len(text) <= MAX_TEXT:
        return text
    return f"{text[:MAX_TEXT]}... [+{len(text) - MAX_TEXT} chars]"


def _indent(text: str) -> str:
    return "\n".join(f"      {line}" for line in _clip(text).splitlines() or [""])


def _box(title: str, lines: list[str]) -> str:
    bar = "=" * WIDTH
    return "\n".join([bar, f" {title}", "-" * WIDTH, *lines, bar])


def log_request(
    completion_id: str,
    payload: dict,
    prompt_messages: list[BaseMessage],
    history_count: int,
    route: str,
    nodes: list[str],
    review: dict,
) -> None:
    roles = " -> ".join(m.type for m in prompt_messages)
    lines = [
        f" id        : {completion_id}",
        f" model     : {payload.get('model')}    stream: {payload.get('stream')}",
        f" route     : {route}",
        f" nodes     : {' -> '.join(nodes)}",
        f" review    : {review['decision'] or 'skipped'}"
        + (f" ({review['reason']})" if review["reason"] else ""),
        f" revisions : {review['revisions']}",
        f" history   : {history_count} earlier message(s) used",
        f" prompt    : {roles}  ({len(prompt_messages)} messages)",
        "",
        " Request payload:",
        _indent(json.dumps(payload, indent=2, ensure_ascii=False)),
        "",
        " Messages sent to the model:",
    ]
    for number, message in enumerate(prompt_messages, start=1):
        lines.append(f"   {number}. [{message.type}]")
        lines.append(_indent(str(message.content)))
    logger.info("\n%s", _box("CHAT REQUEST", lines))


def log_response(
    completion_id: str, answer: str, seconds: float, streamed: bool
) -> None:
    lines = [
        f" id        : {completion_id}",
        f" mode      : {'streamed' if streamed else 'normal'}    time: {seconds:.2f}s",
        f" length    : {len(answer)} chars",
        "",
        " Reply:",
        _indent(answer),
    ]
    logger.info("\n%s", _box("CHAT REPLY", lines))
