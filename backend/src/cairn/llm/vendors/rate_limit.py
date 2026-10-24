"""Rate-limit errors with the delay the vendor asked for (design §10.3), for both SDK adapters."""

import re
from collections.abc import Mapping

from cairn.llm.types import LlmError

_RETRY_AFTER_TEXT = re.compile(r"retry after (\d+(?:\.\d+)?)\s*s", re.IGNORECASE)


def retry_after(headers: Mapping[str, str], message: str) -> float | None:
    """`retry-after-ms`, then `retry-after` in seconds, then the gateway's "Retry after 29s" in
    the message text (the gateway's free-tier 429s carry the delay only there)."""
    for name, scale in (("retry-after-ms", 1000.0), ("retry-after", 1.0)):
        try:
            return float(headers[name]) / scale
        except (KeyError, ValueError):
            continue
    match = _RETRY_AFTER_TEXT.search(message)
    return float(match[1]) if match else None


def rate_limited(vendor: str, headers: Mapping[str, str], message: str) -> LlmError:
    return LlmError(
        f"{vendor}: rate limited: {message}",
        retryable=True,
        code="rate_limited",
        retry_after=retry_after(headers, message),
    )
