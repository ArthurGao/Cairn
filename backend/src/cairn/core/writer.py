"""The one write path into a harness home (design §6.4) and undo (§4.5).

Every write: under the home lock, checked against a base hash, atomic, and logged with its
before/after text in `memory/_changelog.jsonl`. Write-back, cleanup, undo and the CLI all come
through here, so the rules cannot drift.
"""

import hashlib
import json
import os
from collections.abc import Callable, Generator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

from filelock import FileLock, Timeout
from pydantic import BaseModel
from ulid import ULID

from cairn.core.atomic import append_line_durable, write_text_atomic
from cairn.core.index import (
    archive_path,
    index_current,
    index_path,
    memory_path,
    read_index,
)
from cairn.errors import CairnError, Conflict, NotFound

LOCK_TIMEOUT_S = 10
CHANGELOG = Path("memory/_changelog.jsonl")
INDEX_SLUG = "MEMORY"
RECOVERED_NOTE = " [logged after a crash: the file was already written]"

FileOpKind = Literal["create", "update", "archive", "restore"]
OpKind = FileOpKind | Literal["index_sync"]


class LockTimeout(CairnError):
    code = "lock_timeout"
    status = 503


def new_change_id() -> str:
    return f"chg_{ULID()}"


class Op(BaseModel):
    """One file change. `base_hash` is the expected state before it (None = no file).

    create/update: base = live file (None for create); `after` = new full text.
    archive: base = live file; the live file moves to `_archive/`.
    restore: base = the archived file; it moves back; there must be no live file.
    """

    op_id: str
    op: FileOpKind
    slug: str
    after: str | None = None
    base_hash: str | None = None
    reason: str = ""
    undo_of: str | None = None


class OpGroup(BaseModel):
    """All-or-nothing: if any op conflicts, nothing in the group is written."""

    group_id: str
    ops: list[Op]


class ChangeEntry(BaseModel):
    id: str
    op_id: str
    group_id: str
    at: datetime
    actor: str
    op: OpKind
    slug: str
    before: str | None
    after: str | None
    base_hash: str | None
    reason: str
    undo_of: str | None = None


@dataclass
class ApplyResult:
    applied: list[ChangeEntry] = field(default_factory=list[ChangeEntry])
    skipped: list[str] = field(default_factory=list[str])  # op ids already in the log
    rejected: list[tuple[str, str]] = field(default_factory=list[tuple[str, str]])  # group, why


def text_hash(text: str | None) -> str | None:
    return None if text is None else hashlib.sha256(text.encode("utf-8")).hexdigest()


def _read(path: Path) -> str | None:
    return path.read_text(encoding="utf-8") if path.is_file() else None


@contextmanager
def home_lock(home: Path) -> Generator[None]:
    try:
        with FileLock(home / ".cairn.lock", timeout=LOCK_TIMEOUT_S):
            yield
    except Timeout as exc:
        raise LockTimeout(f"the harness home is busy (lock held over {LOCK_TIMEOUT_S}s)") from exc


def _changelog_lines(home: Path) -> list[str]:
    text = _read(home / CHANGELOG) or ""
    return [line for line in text.splitlines() if line.strip()]


def read_changelog(home: Path) -> list[ChangeEntry]:
    return [ChangeEntry.model_validate_json(line) for line in _changelog_lines(home)]


def _logged_op_ids(home: Path) -> set[str]:
    """Op ids only: no need to validate every before/after text on each write."""
    return {json.loads(line)["op_id"] for line in _changelog_lines(home)}


@dataclass(frozen=True)
class _Plan:
    op: Op
    before: str | None  # text the change log records as before
    after: str | None  # text the change log records as after
    done: bool  # the file system already shows this op applied (its log line was lost)
    conflict: str | None


def _plan(home: Path, op: Op) -> _Plan:
    """Where the file system stands for `op`: already applied, safe to apply, or a conflict."""
    live = _read(memory_path(home, op.slug))
    archived = _read(archive_path(home, op.slug))
    if op.op in ("create", "update"):
        # Applied but unlogged (crash): an update's old text is gone, so `before` stays None.
        if live is not None and live == op.after:
            return _Plan(op, None, op.after, True, None)
        ok = text_hash(live) == op.base_hash
        return _Plan(op, live, op.after, False, None if ok else "the file changed")
    if op.op == "archive":
        if live is None and archived is not None and text_hash(archived) == op.base_hash:
            return _Plan(op, archived, None, True, None)
        if archived is not None:
            return _Plan(op, live, None, False, "an archived file with this slug already exists")
        ok = live is not None and text_hash(live) == op.base_hash
        return _Plan(op, live, None, False, None if ok else "the file changed")
    # restore
    if archived is None and live is not None and text_hash(live) == op.base_hash:
        return _Plan(op, None, live, True, None)
    ok = live is None and archived is not None and text_hash(archived) == op.base_hash
    return _Plan(op, None, archived, False, None if ok else "the archive or live file changed")


def apply(
    home: Path,
    groups: Sequence[OpGroup],
    actor: str,
    now: datetime,
    new_id: Callable[[], str] = new_change_id,
) -> ApplyResult:
    """Apply op groups per §6.4 (idempotent by op id; a conflict rejects its whole group)."""
    result = ApplyResult()
    with home_lock(home):
        logged = _logged_op_ids(home)
        for group in groups:
            pending = [op for op in group.ops if op.op_id not in logged]
            result.skipped.extend(op.op_id for op in group.ops if op.op_id in logged)
            plans = [_plan(home, op) for op in pending]
            conflicts = [f"{p.op.slug}: {p.conflict}" for p in plans if p.conflict]
            if conflicts:
                result.rejected.append((group.group_id, "; ".join(conflicts)))
                continue
            for plan in plans:
                if not plan.done:
                    _write(home, plan.op)
                entry = ChangeEntry(
                    id=new_id(),
                    op_id=plan.op.op_id,
                    group_id=group.group_id,
                    at=now,
                    actor=actor,
                    op=plan.op.op,
                    slug=plan.op.slug,
                    before=plan.before,
                    after=plan.after,
                    base_hash=plan.op.base_hash,
                    reason=plan.op.reason + (RECOVERED_NOTE if plan.done else ""),
                    undo_of=plan.op.undo_of,
                )
                append_line_durable(home / CHANGELOG, entry.model_dump_json())
                logged.add(entry.op_id)
                result.applied.append(entry)
        if result.applied:
            current, rendered = index_current(home)
            if not current:
                write_text_atomic(index_path(home), rendered)
    return result


def _write(home: Path, op: Op) -> None:
    live, archived = memory_path(home, op.slug), archive_path(home, op.slug)
    if op.op in ("create", "update"):
        assert op.after is not None, f"{op.op} needs after text"
        write_text_atomic(live, op.after)
    elif op.op == "archive":
        archived.parent.mkdir(parents=True, exist_ok=True)
        os.replace(live, archived)
    else:  # restore
        os.replace(archived, live)


def sync_index(
    home: Path, actor: str, now: datetime, new_id: Callable[[], str] = new_change_id
) -> ChangeEntry | None:
    """Regenerate MEMORY.md from the files when it drifted; logged, never undoable."""
    with home_lock(home):
        current, rendered = index_current(home)
        if current:
            return None
        before = read_index(home)
        write_text_atomic(index_path(home), rendered)
        change_id = new_id()
        entry = ChangeEntry(
            id=change_id,
            op_id=f"index_sync:{change_id}",
            group_id=f"index_sync:{change_id}",
            at=now,
            actor=actor,
            op="index_sync",
            slug=INDEX_SLUG,
            before=before,
            after=rendered,
            base_hash=text_hash(before),
            reason="MEMORY.md re-derived from the memory files",
        )
        append_line_durable(home / CHANGELOG, entry.model_dump_json())
    return entry


# --- undo (§4.5) ----------------------------------------------------------------------------

_INVERSE: dict[FileOpKind, FileOpKind] = {
    "create": "archive",
    "update": "update",
    "archive": "restore",
    "restore": "archive",
}


def _inverse(entry: ChangeEntry, op_id: str) -> Op:
    if entry.op == "index_sync":
        raise Conflict("index_sync changes are re-derived, not undone", code="not_undoable")
    if entry.op == "archive":
        base, after = text_hash(entry.before), entry.before
    elif entry.op == "update":
        base, after = text_hash(entry.after), entry.before
    else:  # create or restore: the file is live with `after`; archive it again
        base, after = text_hash(entry.after), None
    return Op(
        op_id=op_id,
        op=_INVERSE[entry.op],
        slug=entry.slug,
        after=after,
        base_hash=base,
        reason=f"undo {entry.id}",
        undo_of=entry.id,
    )


def undo(
    home: Path,
    change_id: str,
    actor: str,
    now: datetime,
    new_id: Callable[[], str] = new_change_id,
) -> ApplyResult:
    """Undo the whole group `change_id` belongs to, newest entry first, as one new group."""
    log = read_changelog(home)
    target = next((e for e in log if e.id == change_id), None)
    if target is None:
        raise NotFound(f"no change {change_id}", code="change_not_found")
    group = [e for e in log if e.group_id == target.group_id]
    if lost := [e.id for e in group if e.op == "update" and e.before is None]:
        raise Conflict(
            f"cannot undo: the text before {', '.join(lost)} was lost in a crash",
            code="not_undoable",
        )
    ops = [_inverse(e, f"undo:{target.group_id}:{n}") for n, e in enumerate(reversed(group))]
    result = apply(home, [OpGroup(group_id=f"undo:{target.group_id}", ops=ops)], actor, now, new_id)
    if result.rejected:
        raise Conflict(f"cannot undo {change_id}: {result.rejected[0][1]}", code="conflict")
    return result
