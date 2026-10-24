"""Run records (design §4.6): exact file text, write-once, lookup by run id."""

from datetime import UTC, date, datetime
from pathlib import Path

from cairn.core.runs import (
    RunRecord,
    RunTokens,
    recorded_status,
    run_record_path,
    run_records,
    write_run_record,
)

DAY = date(2026, 10, 24)


def _record(run_id: str, status: str = "completed", error: str | None = None) -> RunRecord:
    return RunRecord(
        run_id=run_id,
        started=datetime(2026, 10, 24, 3, 10, 2, tzinfo=UTC),
        status=status,
        tokens=RunTokens(l0=790, loaded=172, baseline_all=1374, input_total=3500, output_total=460),
        loaded=["memory:pilot-scope"],
        applied=2,
        rejected=1,
        error=error,
        task="Draft a cover note",
        outcome="Drafted it.",
        open_items=["Confirm the address"],
    )


def test_record_text_is_the_design_format(tmp_path: Path) -> None:
    assert write_run_record(tmp_path, DAY, _record("R1")) is True
    assert run_record_path(tmp_path, DAY, "R1").read_text() == (
        "---\n"
        "run_id: R1\n"
        "started: '2026-10-24T03:10:02+00:00'\n"
        "status: completed\n"
        "tokens:\n"
        "  l0: 790\n"
        "  loaded: 172\n"
        "  baseline_all: 1374\n"
        "  input_total: 3500\n"
        "  output_total: 460\n"
        "loaded:\n"
        "- memory:pilot-scope\n"
        "writeback:\n"
        "  applied: 2\n"
        "  rejected: 1\n"
        "---\n\n"
        "## Task\nDraft a cover note\n\n## Outcome\nDrafted it.\n\n"
        "## Open items\n- Confirm the address\n"
    )


def test_written_once_and_found_by_run_id(tmp_path: Path) -> None:
    write_run_record(tmp_path, DAY, _record("01RUNA"))
    failed = _record("01RUNB", "failed", "max_steps reached").model_copy(update={"open_items": []})
    write_run_record(tmp_path, date(2026, 10, 25), failed)
    assert write_run_record(tmp_path, DAY, _record("01RUNA", "failed")) is False
    records = run_records(tmp_path)
    assert sorted(records) == ["01RUNA", "01RUNB"]
    assert [recorded_status(records[r]) for r in ("01RUNA", "01RUNB")] == ["completed", "failed"]
    failed_text = records["01RUNB"].read_text()
    assert (
        "error: max_steps reached\n" in failed_text,
        failed_text.endswith("## Open items\n- none\n"),
    ) == (True, True)
    (tmp_path / "state/runs/2026-10-26-BROKEN.md").write_text("no frontmatter")
    assert recorded_status(run_records(tmp_path)["BROKEN"]) is None
    assert run_records(tmp_path / "missing") == {}
