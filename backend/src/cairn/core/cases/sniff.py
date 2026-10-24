"""Decide an upload's media type from its bytes, never from what the client claims (§13)."""

from pathlib import PurePath

from cairn.errors import Unsupported

_MAGIC: list[tuple[bytes, str, str]] = [
    (b"%PDF-", "application/pdf", "pdf"),
    (b"\x89PNG\r\n\x1a\n", "image/png", "png"),
    (b"\xff\xd8\xff", "image/jpeg", "jpg"),
]
_TEXT_SUFFIXES = {".txt": ("text/plain", "txt"), ".md": ("text/markdown", "md")}


def sniff(filename: str, data: bytes) -> tuple[str, str]:
    """Return (media type, stored extension) or raise `unsupported_type`."""
    for magic, media_type, ext in _MAGIC:
        if data.startswith(magic):
            return media_type, ext
    suffix = PurePath(filename).suffix.lower()
    if suffix in _TEXT_SUFFIXES and b"\x00" not in data:
        try:
            data.decode("utf-8")
        except UnicodeDecodeError:
            pass
        else:
            return _TEXT_SUFFIXES[suffix]
    raise Unsupported(
        f"{filename}: only PDF, PNG, JPEG, plain text and Markdown files are accepted"
    )
