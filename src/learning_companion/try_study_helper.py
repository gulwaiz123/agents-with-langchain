"""Development helper: ask the study-helper chain one question from the command line.

Usage: uv run python -m learning_companion.try_study_helper "What is a variable?"
"""

import sys

from learning_companion.chain import ConfigurationError, build_study_helper_chain
from learning_companion.config import get_settings


def main() -> int:
    question = " ".join(sys.argv[1:]).strip()
    if not question:
        print('Usage: python -m learning_companion.try_study_helper "your question"')
        return 2
    try:
        chain = build_study_helper_chain(get_settings())
    except ConfigurationError as error:
        print(f"Configuration error: {error}")
        return 1
    print(chain.invoke({"history": [], "question": question}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
