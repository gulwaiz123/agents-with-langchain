"""The one visible routing rule: plain Python, no model involved.

If the latest user message starts with `/study`, use the study helper.
Otherwise use general chat.
"""

import re

GENERAL = "general"
STUDY = "study"

# "/study" must be the whole first word, so "/studying" stays general chat.
_STUDY_MARKER = re.compile(r"^/study(?:\s+|$)")


def choose_route(question: str) -> tuple[str, str]:
    """Return (route, question). Only the leading `/study` marker is removed."""
    text = question.lstrip()
    if _STUDY_MARKER.match(text):  # if ...
        return STUDY, _STUDY_MARKER.sub("", text, count=1)
    return GENERAL, question  # ... else
