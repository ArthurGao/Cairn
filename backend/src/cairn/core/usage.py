"""Per-memory read statistics in `state/usage.json` (design §4.4, D-06)."""

import json
from collections.abc import Iterable
from datetime import date
from pathlib import Path

from pydantic import TypeAdapter

from cairn.core.atomic import write_text_atomic
from cairn.core.model import Model

USAGE_FILE = Path("state/usage.json")


class UsageEntry(Model):
    reads: int = 0
    last_read: date | None = None
    written_by_runs: int = 0


_USAGE = TypeAdapter(dict[str, UsageEntry])


def load_usage(home: Path) -> dict[str, UsageEntry]:
    path = home / USAGE_FILE
    if not path.is_file():
        return {}
    return _USAGE.validate_json(path.read_text(encoding="utf-8"))


def save_usage(home: Path, usage: dict[str, UsageEntry]) -> None:
    """One entry per line in existing order (new slugs last): small diffs in a git-kept home."""
    lines = [f"  {json.dumps(slug)}: {_entry(usage[slug])}" for slug in usage]
    write_text_atomic(home / USAGE_FILE, "{\n" + ",\n".join(lines) + "\n}\n")


def _entry(entry: UsageEntry) -> str:
    fields = ", ".join(
        f"{json.dumps(k)}: {json.dumps(v)}" for k, v in entry.model_dump(mode="json").items()
    )
    return "{ " + fields + " }"


def record_run(
    usage: dict[str, UsageEntry], read: Iterable[str], written: Iterable[str], today: date
) -> dict[str, UsageEntry]:
    """New usage after a run that read and wrote these slugs (each counted once per run)."""
    updated = {slug: entry.model_copy() for slug, entry in usage.items()}
    for slug in set(read):
        entry = updated.setdefault(slug, UsageEntry())
        entry.reads += 1
        entry.last_read = today
    for slug in set(written):
        updated.setdefault(slug, UsageEntry()).written_by_runs += 1
    return updated
