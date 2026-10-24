"""Atomic file writes: readers never see a half-written file (design §6.4, §13)."""

import os
import uuid
from pathlib import Path


def write_bytes_atomic(path: Path, data: bytes) -> None:
    """Write to a temp file beside `path`, fsync, then rename over it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp-{uuid.uuid4().hex}")
    try:
        with tmp.open("wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def write_text_atomic(path: Path, text: str) -> None:
    write_bytes_atomic(path, text.encode("utf-8"))


def append_line_durable(path: Path, line: str) -> None:
    """Append one line to an append-only log and fsync it (callers hold the relevant lock)."""
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
        handle.flush()
        os.fsync(handle.fileno())
