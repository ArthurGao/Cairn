"""Write-back validation (design §6.3): the model proposes, these rules decide."""

from datetime import UTC, date, datetime
from pathlib import Path

from cairn.core.index import memory_path
from cairn.core.validate import ProposedOp, WritebackPlan, conflict_rejections, plan_writeback
from cairn.core.writer import apply, text_hash

TODAY = date(2026, 10, 25)
NOW = datetime(2026, 10, 25, 1, 0, tzinfo=UTC)
SOURCES = [
    "Task: draft the cover note for case 7",
    "Answer: ... the adviser said always write dates as 24 October 2026 in cover notes ...",
]


def _op(**kw: object) -> ProposedOp:
    base: dict[str, object] = {
        "op": "create",
        "slug": "cover-note-dates",
        "type": "feedback",
        "description": "Cover notes write dates as day month year",
        "body": "Write dates as 24 October 2026.\n\n**Why:** INZ reads them.\n"
        "**How to apply:** every cover note.",
        "evidence": ["always write dates as 24 October 2026"],
        "reason": "adviser preference",
    }
    return ProposedOp.model_validate(base | kw)


def _plan(home: Path, *ops: ProposedOp, read_hashes: dict[str, str] | None = None) -> WritebackPlan:
    return plan_writeback(
        home, list(ops), SOURCES, "01RUN", read_hashes or {}, TODAY, dup_threshold=0.82
    )


def test_accepted_create_is_rendered_by_code(home: Path) -> None:
    plan = _plan(home, _op())
    assert plan.rejected == []
    [group] = plan.groups
    [op] = group.ops
    assert (group.group_id, op.op_id, op.op, op.slug, op.base_hash) == (
        "01RUN:0",
        "01RUN:0",
        "create",
        "cover-note-dates",
        None,
    )
    assert op.after == (
        "---\nname: cover-note-dates\ndescription: Cover notes write dates as day month year\n"
        "metadata:\n  type: feedback\n  created: 2026-10-25\n  updated: 2026-10-25\n"
        "  source_run: 01RUN\n---\n\nWrite dates as 24 October 2026.\n\n**Why:** INZ reads them.\n"
        "**How to apply:** every cover note.\n"
    )


def test_update_keeps_created_and_unknown_keys(home: Path) -> None:
    path = memory_path(home, "pilot-scope")
    path.write_text(path.read_text().replace("metadata:\n", "owner_tool: other\nmetadata:\n"))
    original = path.read_text()
    update = _op(
        op="update",
        slug="pilot-scope",
        type="project",
        description="Pilot covers AEWV cases only, on synthetic documents",
        body="Pilot runs AEWV only.\n\n**Why:** scope.\n**How to apply:** refuse others.",
        evidence=["draft the cover note"],
    )
    plan = _plan(home, update)
    [op] = plan.groups[0].ops
    assert op.base_hash == text_hash(original)  # not read during the run: hash taken now
    assert op.after is not None
    assert "owner_tool: other\n" in op.after
    assert "  created: 2026-10-01\n  updated: 2026-10-25\n  source_run: 01RUN\n" in op.after
    assert op.after.endswith(
        "\n---\n\nPilot runs AEWV only.\n\n**Why:** scope.\n**How to apply:** refuse others.\n"
    )
    read = _plan(home, update, read_hashes={"pilot-scope": "hash-from-read"})
    assert read.groups[0].ops[0].base_hash == "hash-from-read"


def test_each_rule_rejects_with_its_code_and_others_proceed(home: Path) -> None:
    plan = _plan(
        home,
        _op(slug="Bad Slug"),
        _op(slug="no-evidence", evidence=[]),
        _op(slug="made-up", evidence=["the adviser never said this"]),
        _op(slug="has-secret", body="Use key sk-ant-api03-abcdefgh1234"),
        _op(slug="has-person", body="Client passport XS0000001 expires soon"),
    )
    assert [(r.index, r.slug, r.code) for r in plan.rejected] == [
        (0, "Bad Slug", "schema"),
        (1, "no-evidence", "evidence_missing"),
        (2, "made-up", "evidence_missing"),
        (3, "has-secret", "secret"),
        (4, "has-person", "personal_data"),
    ]
    assert plan.rejected[3].reason == "matches the anthropic_key pattern"
    assert plan.groups == []
    second = _plan(
        home,
        _op(slug="fine-one"),
        _op(
            slug="near-dup",
            description="Phrase each conflict as a question to confirm, never an accusation",
        ),
        _op(op="update", slug="does-not-exist"),
    )
    assert [(r.index, r.slug, r.code) for r in second.rejected] == [
        (1, "near-dup", "duplicate"),
        (2, "does-not-exist", "not_found"),
    ]
    assert second.rejected[0].reason == "description is 1.00 similar to conflicts-as-questions"
    assert [(g.group_id, g.ops[0].slug) for g in second.groups] == [("01RUN:0", "fine-one")]


def test_first_failing_rule_wins(home: Path) -> None:
    plan = _plan(home, _op(slug="two-problems", evidence=[], body="password: x"))
    assert [r.code for r in plan.rejected] == ["evidence_missing"]


def test_schema_covers_type_and_lengths(home: Path) -> None:
    plan = _plan(
        home,
        _op(slug="bad-type", type="opinion"),
        _op(slug="long-description", description="d" * 151),
        _op(slug="long-body", body="b" * 2001),
    )
    assert [(r.slug, r.code) for r in plan.rejected] == [
        ("bad-type", "schema"),
        ("long-description", "schema"),
        ("long-body", "schema"),
    ]


def test_ops_after_the_fifth_are_rejected_unread(home: Path) -> None:
    ops = [
        _op(slug=f"note-{n}", description=f"Distinct topic number {n} for cover notes")
        for n in range(7)
    ]
    plan = _plan(home, *ops)
    assert [(r.index, r.code) for r in plan.rejected] == [(5, "run_limit"), (6, "run_limit")]
    assert len(plan.groups) == 5


def test_writer_conflicts_map_to_the_conflict_code(home: Path) -> None:
    update = _op(op="update", slug="pilot-scope", type="project")
    plan = _plan(home, update, read_hashes={"pilot-scope": "stale"})
    result = apply(home, plan.groups, "run:01RUN", NOW)
    assert [(r.index, r.slug, r.code) for r in conflict_rejections(plan, result)] == [
        (0, "pilot-scope", "conflict")
    ]


def test_reason_is_scanned_because_the_changelog_keeps_it(home: Path) -> None:
    plan = _plan(
        home,
        _op(slug="leaky-reason", reason="user pasted sk-ant-api03-abcdefgh1234"),
        _op(slug="personal-reason", reason="client alex@example.test asked"),
    )
    assert [(r.slug, r.code) for r in plan.rejected] == [
        ("leaky-reason", "secret"),
        ("personal-reason", "personal_data"),
    ]
