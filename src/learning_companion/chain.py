from typing import Literal

from langchain_core.messages import BaseMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
)
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

from learning_companion.config import Settings

LEARNING_COMPANION_INSTRUCTION = (
    "You are the Learning Companion, a friendly helper for people who are new "
    "to a topic. Explain things in short, plain English and give one small "
    "example when it helps."
)


# Part 1 of the prompt: owned by the application, never changed by a request.
SYSTEM_MESSAGE = SystemMessage(content=LEARNING_COMPANION_INSTRUCTION)
# Part 2: recent messages of this chat, supplied by the current request only.
HISTORY_PLACEHOLDER = MessagesPlaceholder("history")
# Part 3 of the prompt: the participant's current message.
USER_MESSAGE_TEMPLATE = HumanMessagePromptTemplate.from_template("{question}")

PROMPT = ChatPromptTemplate.from_messages(
    [SYSTEM_MESSAGE, HISTORY_PLACEHOLDER, USER_MESSAGE_TEMPLATE]
)


def describe_prompt(history: list[BaseMessage], question: str) -> str:
    """Roles and count only: safe to log (no text, no keys)."""
    messages = PROMPT.format_messages(history=history, question=question)
    roles = [message.type for message in messages]
    return f"roles={roles} count={len(roles)}"


class ConfigurationError(Exception):
    """Raised when a model call is attempted without the required settings."""


STUDY_HELPER_INSTRUCTION = (
    "You are the Learning Companion's study helper for beginners. Explain the "
    "technical idea the user asks about in concise, plain language. Add a small "
    "example where it helps. Always end with exactly one suggested next "
    "learning step. You cannot search, browse or look up course material, and "
    "you may make mistakes, so do not claim research or guaranteed correctness."
)

# Same structure as the general chat prompt, with its own application-owned instruction.
STUDY_HELPER_PROMPT = ChatPromptTemplate.from_messages(
    [
        SystemMessage(content=STUDY_HELPER_INSTRUCTION),
        HISTORY_PLACEHOLDER,
        USER_MESSAGE_TEMPLATE,
    ]
)


def build_model(settings: Settings) -> ChatGoogleGenerativeAI:
    missing = [
        name
        for name, value in (
            ("GEMINI_API_KEY", settings.gemini_api_key),
            ("GEMINI_MODEL_NAME", settings.gemini_model_name),
        )
        if not value
    ]
    if missing:
        raise ConfigurationError(
            f"Missing setting(s): {', '.join(missing)}. Set them in your .env file."
        )

    return ChatGoogleGenerativeAI(
        model=settings.gemini_model_name,
        api_key=settings.gemini_api_key,
    )


def build_chain(settings: Settings):
    """General chat: greetings and ordinary conversation (used by the endpoint)."""
    return PROMPT | build_model(settings) | StrOutputParser()


def build_study_helper_chain(settings: Settings):
    """Study helper: beginner explanation plus one next step (not yet routed)."""
    return STUDY_HELPER_PROMPT | build_model(settings) | StrOutputParser()


# --- Story 4.2: reviewer and improver (small LLM specialist nodes) ---------

REVIEW_RULE = (
    "Classroom rule for a good answer: it is plain English and easy for a "
    "beginner. It matches its role. General chat is friendly and brief. Study "
    "help gives a short explanation and ends with exactly one suggested next "
    "learning step. It never claims to browse, research or look things up."
)


class ReviewResult(BaseModel):
    decision: Literal["approve", "improve"] = Field(
        description="approve if the draft follows the rule, otherwise improve"
    )
    reason: str = Field(description="one short plain-English sentence")


REVIEWER_PROMPT = ChatPromptTemplate.from_messages(
    [
        SystemMessage(
            content=(
                "You review one draft answer from a beginner learning chatbot. "
                + REVIEW_RULE
                + " Decide approve or improve, and give one short reason. "
                "Only choose improve when the draft clearly breaks the rule."
            )
        ),
        HumanMessagePromptTemplate.from_template(
            "Role: {route}\nQuestion: {question}\n\nDraft answer:\n{draft}"
        ),
    ]
)

IMPROVER_PROMPT = ChatPromptTemplate.from_messages(
    [
        SystemMessage(
            content=(
                "You rewrite one draft answer once, fixing the problem the "
                "reviewer named. Keep the same role and meaning. "
                + REVIEW_RULE
                + " Reply with the improved answer only."
            )
        ),
        HumanMessagePromptTemplate.from_template(
            "Role: {route}\nQuestion: {question}\n\nDraft answer:\n{draft}\n\n"
            "Reviewer's reason: {reason}"
        ),
    ]
)


def build_reviewer_chain(settings: Settings):
    """Returns a ReviewResult (decision + reason)."""
    model = build_model(settings).with_structured_output(ReviewResult)
    return REVIEWER_PROMPT | model


def build_improver_chain(settings: Settings):
    """Returns the rewritten answer text."""
    return IMPROVER_PROMPT | build_model(settings) | StrOutputParser()
