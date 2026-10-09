from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from learning_companion.config import Settings

LEARNING_COMPANION_INSTRUCTION = (
    "You are the Learning Companion, a friendly helper for people who are new "
    "to a topic. Explain things in short, plain English and give one small "
    "example when it helps."
)


class ConfigurationError(Exception):
    """Raised when a model call is attempted without the required settings."""


def build_chain(settings: Settings):
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

    prompt = ChatPromptTemplate.from_messages(
        [("system", LEARNING_COMPANION_INSTRUCTION), ("human", "{question}")]
    )
    model = ChatGoogleGenerativeAI(
        model=settings.gemini_model_name,
        api_key=settings.gemini_api_key,
    )
    return prompt | model | StrOutputParser()
