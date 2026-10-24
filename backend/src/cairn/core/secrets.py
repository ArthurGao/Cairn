"""Patterns that must never be written into the harness home (design §6.3 `secret`,
`personal_data`). A match names the pattern, never echoes the value."""

import re

SECRET_PATTERNS: dict[str, re.Pattern[str]] = {
    "anthropic_key": re.compile(r"sk-ant-[A-Za-z0-9_-]{8,}"),
    "api_key": re.compile(r"\bsk-[A-Za-z0-9_-]{16,}"),
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "github_token": re.compile(r"\bghp_[A-Za-z0-9]{20,}"),
    "slack_token": re.compile(r"\bxox[bp]-[A-Za-z0-9-]{10,}"),
    "private_key": re.compile(r"-----BEGIN"),
    "password": re.compile(r"password\s*[:=]", re.IGNORECASE),
    "hex_run": re.compile(r"\b[0-9a-fA-F]{40,}\b"),
}
_BASE64_RUN = re.compile(r"[A-Za-z0-9+/]{40,}={0,2}")

PERSONAL_PATTERNS: dict[str, re.Pattern[str]] = {
    "email": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    "phone": re.compile(r"(?<![\w-])\+?\d(?:[ ]?\d){7,14}(?![\w-])"),
    "passport_number": re.compile(r"\b[A-Z]{1,2}\d{6,9}\b"),
    "date_of_birth": re.compile(r"\b(?:born|dob|date of birth)\b\W{0,3}\d", re.IGNORECASE),
}


def find_secret(text: str) -> str | None:
    """Name of the first secret pattern found, else None."""
    for name, pattern in SECRET_PATTERNS.items():
        if pattern.search(text):
            return name
    for run in _BASE64_RUN.findall(text):
        # A run that mixes letters and digits; plain words and paths do not.
        if re.search(r"\d", run) and re.search(r"[A-Za-z]", run):
            return "base64_run"
    return None


def find_personal_data(text: str) -> str | None:
    for name, pattern in PERSONAL_PATTERNS.items():
        if pattern.search(text):
            return name
    return None
