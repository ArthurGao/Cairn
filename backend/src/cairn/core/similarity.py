"""Lexical similarity for duplicate detection (design §7.2, D-09)."""

import re

from rapidfuzz import fuzz

STOP_WORDS = frozenset(
    [
        "a",
        "an",
        "the",
        "of",
        "to",
        "and",
        "or",
        "for",
        "in",
        "on",
        "is",
        "are",
        "be",
        "by",
        "with",
        "it",
        "its",
        "as",
        "at",
        "so",
        "first",
        "then",
        "before",
        "after",
        "them",
        "they",
    ]
)
_TOKEN = re.compile(r"[a-z0-9:]+")


def normalise(text: str) -> str:
    return " ".join(t for t in _TOKEN.findall(text.lower()) if t not in STOP_WORDS)


def similarity(a: str, b: str) -> float:
    """token_set_ratio on normalised text, in 0..1."""
    return normalised_similarity(normalise(a), normalise(b))


def normalised_similarity(a: str, b: str) -> float:
    """`similarity` for text already passed through `normalise` (normalise once, compare many)."""
    return fuzz.token_set_ratio(a, b) / 100
