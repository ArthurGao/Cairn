"""Findings never decide which version is right or suggest a document is false (§8.4)."""

import re
from collections.abc import Sequence

_BANNED = re.compile(
    r"\b(fraud|forged|fake|false|falsif|lie|liar|fabricat|incorrect|wrong)", re.IGNORECASE
)


def uses_banned_wording(text: str) -> bool:
    return _BANNED.search(text) is not None


def template_question(statements: Sequence[tuple[str, int, str]]) -> str:
    """Neutral question from (document name, page, value) triples, in the given order."""
    parts = [f"{doc} (page {page}) gives {value}" for doc, page, value in statements]
    return "; ".join(parts) + ". Which is correct?"


def template_summary(category: str, statements: Sequence[tuple[str, int, str]]) -> str:
    values = ", ".join(f"{value} ({doc})" for doc, _, value in statements)
    return f"{category} differs across documents: {values}"
