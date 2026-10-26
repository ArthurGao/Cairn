"""The vendor's own error message for both SDK adapters (design §10.3), without the raw body.

Anthropic, OpenAI and the Vercel gateway all put a human message at `error.message`; the SDK's
own message embeds the whole body (routing metadata, provider attempts), which then reached a
failed document's error in the UI.
"""

MAX_CHARS = 300


def api_message(body: object, fallback: str) -> str:
    """`error.message` from a decoded error body, else the SDK's message; at most MAX_CHARS.

    The anthropic SDK keeps the whole body; the openai SDK keeps only its `error` object.
    """
    error = body.get("error", body) if isinstance(body, dict) else None
    message = error.get("message") if isinstance(error, dict) else None
    text = message if isinstance(message, str) and message else fallback
    return text if len(text) <= MAX_CHARS else text[: MAX_CHARS - 1] + "…"
