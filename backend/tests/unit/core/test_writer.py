"""The one write path (design §6.4) and undo (§4.5)."""

from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from itertools import count
from pathlib import Path

import pytest
from filelock import FileLock

from cairn.core import writer
from cairn.core.formats import parse_memory, serialise
from cairn.core.index import archive_path, indexed_slugs, memory_path, read_index
from cairn.core.writer import Op, OpGroup, apply, read_changelog, text_hash, undo
from cairn.errors import CairnError

NOW = datetime(2026, 10, 24, 3, 12, 9, tzinfo=UTC)


@pytest.fixture
def ids() -> Callable[[], str]:
    counter: Iterator[int] = count(1)
    return lambda: f"chg_{next(counter)}"


def _new_memory(slug: str, description: str = "When filing an AEWV") -> str:
    return (
        f"---\nname: {slug}\ndescription: {description}\nmetadata:\n  type: reference\n"
        f"  created: 2026-10-24\n  updated: 2026-10-24\n---\n\nA new note.\n"
    )


def _edited(home: Path, slug: str, body: str) -> str:
    memory = parse_memory(memory_path(home, slug).read_text())
    memory.body = body
    return serialise(memory)


def _group(group_id: str, *ops: Op) -> OpGroup:
    return OpGroup(group_id=group_id, ops=list(ops))


def test_create_update_archive_restore_with_log_and_index(
    home: Path, ids: Callable[[], str]
) -> None:
    created = _new_memory("aewv-forms")
    r1 = apply(
        home,
        [_group("g1", Op(op_id="run1:0", op="create", slug="aewv-forms", after=created))],
        "run:1",
        NOW,
        ids,
    )
    assert memory_path(home, "aewv-forms").read_text() == created
    assert "aewv-forms" in indexed_slugs(read_index(home))
    old = memory_path(home, "pilot-scope").read_text()
    new = _edited(home, "pilot-scope", "Pilot runs AEWV only.\n")
    apply(
        home,
        [
            _group(
                "g2",
                Op(
                    op_id="u:0",
                    op="update",
                    slug="pilot-scope",
                    after=new,
                    base_hash=text_hash(old),
                ),
            ),
            _group(
                "g3",
                Op(op_id="a:0", op="archive", slug="aewv-forms", base_hash=text_hash(created)),
            ),
        ],
        "user",
        NOW,
        ids,
    )
    assert memory_path(home, "pilot-scope").read_text() == new
    assert not memory_path(home, "aewv-forms").exists()
    assert archive_path(home, "aewv-forms").read_text() == created
    assert "aewv-forms" not in indexed_slugs(read_index(home))
    apply(
        home,
        [
            _group(
                "g4", Op(op_id="r:0", op="restore", slug="aewv-forms", base_hash=text_hash(created))
            )
        ],
        "user",
        NOW,
        ids,
    )
    assert memory_path(home, "aewv-forms").read_text() == created
    log = read_changelog(home)
    assert [(e.id, e.op_id, e.op, e.slug, e.actor) for e in log] == [
        ("chg_1", "run1:0", "create", "aewv-forms", "run:1"),
        ("chg_2", "u:0", "update", "pilot-scope", "user"),
        ("chg_3", "a:0", "archive", "aewv-forms", "user"),
        ("chg_4", "r:0", "restore", "aewv-forms", "user"),
    ]
    assert (log[0].before, log[0].after) == (None, created)
    assert (log[1].before, log[1].after) == (old, new)
    assert (log[2].before, log[2].after) == (created, None)
    assert (log[3].before, log[3].after) == (None, created)
    assert r1.applied[0].at == NOW


def test_conflict_rejects_the_whole_group(home: Path, ids: Callable[[], str]) -> None:
    keep = memory_path(home, "checklist-owner").read_text()
    result = apply(
        home,
        [
            _group(
                "merge",
                Op(
                    op_id="m:0",
                    op="update",
                    slug="conflicts-as-questions",
                    after="changed",
                    base_hash=text_hash(memory_path(home, "conflicts-as-questions").read_text()),
                ),
                Op(op_id="m:1", op="archive", slug="checklist-owner", base_hash="stale-hash"),
            )
        ],
        "cleanup:wf1",
        NOW,
        ids,
    )
    assert result.applied == []
    assert result.rejected == [("merge", "checklist-owner: the file changed")]
    assert "changed" not in memory_path(home, "conflicts-as-questions").read_text()
    assert memory_path(home, "checklist-owner").read_text() == keep
    assert read_changelog(home) == []


def test_create_onto_an_existing_file_conflicts(home: Path, ids: Callable[[], str]) -> None:
    op = Op(op_id="c:0", op="create", slug="pilot-scope", after=_new_memory("pilot-scope"))
    result = apply(home, [_group("g", op)], "run:2", NOW, ids)
    assert result.rejected == [("g", "pilot-scope: the file changed")]


def test_reapplying_is_idempotent(home: Path, ids: Callable[[], str]) -> None:
    group = _group("g", Op(op_id="run9:0", op="create", slug="n1", after=_new_memory("n1")))
    apply(home, [group], "run:9", NOW, ids)
    again = apply(home, [group], "run:9", NOW, ids)
    assert (again.applied, again.skipped, again.rejected) == ([], ["run9:0"], [])
    assert len(read_changelog(home)) == 1


def test_lost_log_line_is_recovered_by_content(home: Path, ids: Callable[[], str]) -> None:
    text = _new_memory("n2")
    memory_path(home, "n2").write_text(text)  # written, then the process died before logging
    result = apply(
        home,
        [_group("g", Op(op_id="run3:0", op="create", slug="n2", after=text))],
        "run:3",
        NOW,
        ids,
    )
    assert [(e.op_id, e.before, e.after) for e in result.applied] == [("run3:0", None, text)]
    assert result.applied[0].reason.endswith(writer.RECOVERED_NOTE)
    assert result.rejected == []


def test_recovered_update_cannot_be_undone(home: Path, ids: Callable[[], str]) -> None:
    old = memory_path(home, "pilot-scope").read_text()
    new = _edited(home, "pilot-scope", "v2\n")
    memory_path(home, "pilot-scope").write_text(new)  # crash after write, before the log line
    op = Op(op_id="u:0", op="update", slug="pilot-scope", after=new, base_hash=text_hash(old))
    apply(home, [_group("g", op)], "user", NOW, ids)
    with pytest.raises(CairnError) as info:
        undo(home, "chg_1", "user", NOW, ids)
    assert (info.value.code, info.value.message) == (
        "not_undoable",
        "cannot undo: the text before chg_1 was lost in a crash",
    )
    assert memory_path(home, "pilot-scope").read_text() == new


def test_undo_restores_a_whole_merge_group(home: Path, ids: Callable[[], str]) -> None:
    target_old = memory_path(home, "conflicts-as-questions").read_text()
    member_old = memory_path(home, "neutral-wording-for-discrepancies").read_text()
    merged = _edited(home, "conflicts-as-questions", "Merged body.\n")
    apply(
        home,
        [
            _group(
                "merge-1",
                Op(
                    op_id="wf:merge:0",
                    op="update",
                    slug="conflicts-as-questions",
                    after=merged,
                    base_hash=text_hash(target_old),
                ),
                Op(
                    op_id="wf:merge:1",
                    op="archive",
                    slug="neutral-wording-for-discrepancies",
                    base_hash=text_hash(member_old),
                ),
            )
        ],
        "cleanup:wf",
        NOW,
        ids,
    )
    result = undo(home, "chg_1", "user", NOW, ids)
    assert memory_path(home, "conflicts-as-questions").read_text() == target_old
    assert memory_path(home, "neutral-wording-for-discrepancies").read_text() == member_old
    assert not archive_path(home, "neutral-wording-for-discrepancies").exists()
    assert [(e.op, e.slug, e.undo_of, e.group_id) for e in result.applied] == [
        ("restore", "neutral-wording-for-discrepancies", "chg_2", "undo:merge-1"),
        ("update", "conflicts-as-questions", "chg_1", "undo:merge-1"),
    ]
    assert (
        read_index(home)
        == (Path(__file__).parents[2] / "fixtures/home/memory/MEMORY.md").read_text()
    )
    assert undo(home, "chg_2", "user", NOW, ids).skipped == ["undo:merge-1:0", "undo:merge-1:1"]


def test_undo_of_a_create_archives_it(home: Path, ids: Callable[[], str]) -> None:
    text = _new_memory("n3")
    apply(home, [_group("g", Op(op_id="r:0", op="create", slug="n3", after=text))], "run", NOW, ids)
    undo(home, "chg_1", "user", NOW, ids)
    assert not memory_path(home, "n3").exists()
    assert archive_path(home, "n3").read_text() == text


def test_undo_refuses_when_the_file_changed_since(home: Path, ids: Callable[[], str]) -> None:
    old = memory_path(home, "pilot-scope").read_text()
    new = _edited(home, "pilot-scope", "v2\n")
    op = Op(op_id="u:0", op="update", slug="pilot-scope", after=new, base_hash=text_hash(old))
    apply(home, [_group("g", op)], "user", NOW, ids)
    memory_path(home, "pilot-scope").write_text(_edited(home, "pilot-scope", "hand edit\n"))
    with pytest.raises(CairnError) as info:
        undo(home, "chg_1", "user", NOW, ids)
    assert (info.value.code, info.value.status) == ("conflict", 409)
    assert "hand edit" in memory_path(home, "pilot-scope").read_text()


def test_undo_errors(home: Path, ids: Callable[[], str]) -> None:
    with pytest.raises(CairnError) as info:
        undo(home, "chg_404", "user", NOW, ids)
    assert info.value.code == "change_not_found"
    (home / "memory/MEMORY.md").write_text("# Memory\n")
    entry = writer.sync_index(home, "cli", NOW, ids)
    assert entry is not None
    assert (entry.op, entry.slug, entry.before) == ("index_sync", "MEMORY", "# Memory\n")
    assert writer.sync_index(home, "cli", NOW, ids) is None  # already current: nothing logged
    assert len(read_changelog(home)) == 1
    with pytest.raises(CairnError) as info:
        undo(home, "chg_1", "user", NOW, ids)
    assert info.value.code == "not_undoable"


def test_lock_timeout_is_retryable(home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(writer, "LOCK_TIMEOUT_S", 0.05)
    with FileLock(home / ".cairn.lock"), pytest.raises(CairnError) as info:
        apply(home, [], "user", NOW)
    assert (info.value.code, info.value.status) == ("lock_timeout", 503)


def test_recovered_archive_and_restore_log_the_right_text(
    home: Path, ids: Callable[[], str]
) -> None:
    text = memory_path(home, "checklist-owner").read_text()
    archive_path(home, "checklist-owner").write_text(text)
    memory_path(home, "checklist-owner").unlink()  # moved, then the process died
    op = Op(op_id="a:0", op="archive", slug="checklist-owner", base_hash=text_hash(text))
    apply(home, [_group("g1", op)], "user", NOW, ids)
    memory_path(home, "checklist-owner").write_text(text)
    archive_path(home, "checklist-owner").unlink()  # restored, then the process died
    op = Op(op_id="r:0", op="restore", slug="checklist-owner", base_hash=text_hash(text))
    apply(home, [_group("g2", op)], "user", NOW, ids)
    assert [(e.op, e.before, e.after) for e in read_changelog(home)] == [
        ("archive", text, None),
        ("restore", None, text),
    ]


@pytest.mark.parametrize("slug", ["../escape", "a/b", "Bad_Slug", "", "x" * 65, "_changelog"])
def test_slugs_that_could_escape_memory_are_rejected(
    home: Path, ids: Callable[[], str], slug: str
) -> None:
    op = Op(op_id="c:0", op="create", slug=slug, after=_new_memory("x"))
    with pytest.raises(CairnError) as info:
        apply(home, [_group("g", op)], "run", NOW, ids)
    assert (info.value.code, info.value.status) == ("invalid_slug", 422)
    assert not (home / "escape.md").exists()
    assert read_changelog(home) == []
