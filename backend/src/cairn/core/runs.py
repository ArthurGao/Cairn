"""Run records: `state/runs/<date>-<run_id>.md`, one per agent run (design §4.6)."""

from datetime import date, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from cairn.core.atomic import write_text_atomic
from cairn.core.formats import Document, FormatError, parse_document, serialise

RUNS_DIR = Path("state/runs")
_DATE_PREFIX = len("2026-01-01-")


class RunTokens(BaseModel):
    l0: int = 0
    loaded: int = 0  # estimated tokens of what tools loaded on demand
    baseline_all: int = 0
    input_total: int = 0  # reported by the vendor
    output_total: int = 0


class RunRecord(BaseModel):
    run_id: str
    started: datetime
    status: str
    tokens: RunTokens
    loaded: list[str] = Field(default_factory=list[str])
    applied: int = 0
    rejected: int = 0
    error: str | None = None
    task: str
    outcome: str = ""
    open_items: list[str] = Field(default_factory=list[str])


def run_record_path(home: Path, day: date, run_id: str) -> Path:
    return home / RUNS_DIR / f"{day.isoformat()}-{run_id}.md"


def render_run_record(record: RunRecord) -> str:
    front: dict[str, Any] = {
        "run_id": record.run_id,
        "started": record.started.isoformat(),
        "status": record.status,
        "tokens": record.tokens.model_dump(),
        "loaded": record.loaded,
        "writeback": {"applied": record.applied, "rejected": record.rejected},
    }
    if record.error:
        front["error"] = record.error
    items = "".join(f"- {item}\n" for item in record.open_items) or "- none\n"
    body = f"## Task\n{record.task}\n\n## Outcome\n{record.outcome}\n\n## Open items\n{items}"
    return serialise(Document(front, body))


def write_run_record(home: Path, day: date, record: RunRecord) -> bool:
    """Write once: False (and nothing written) when the run is already recorded.
    Callers hold the home lock."""
    path = run_record_path(home, day, record.run_id)
    if path.exists():
        return False
    write_text_atomic(path, render_run_record(record))
    return True


def run_records(home: Path) -> dict[str, Path]:
    """run_id -> record file, from one directory listing."""
    return {p.stem[_DATE_PREFIX:]: p for p in (home / RUNS_DIR).glob("*.md")}


def recorded_status(path: Path) -> str | None:
    try:
        status = parse_document(path.read_text(encoding="utf-8")).front.get("status")
    except FormatError:
        return None
    return str(status) if status else None
