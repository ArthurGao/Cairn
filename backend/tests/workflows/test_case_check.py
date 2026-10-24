"""CaseCheckWorkflow end to end on the synthetic sample case (design §8, §14).

Real activities against a tmp case store, the fake vendor replaying
tests/fixtures/llm/aewv_sample.json, and replay of every produced history for determinism.
"""

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from temporalio.client import Client, WorkflowHistory
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Replayer

from cairn.core.cases import store
from cairn.core.cases.models import CheckResult
from cairn.llm.client import build_client
from cairn.settings import Settings
from cairn.worker import WORKFLOWS, build_worker
from cairn.workflows.case_check import CaseCheckWorkflow
from cairn.workflows.case_models import CheckInput, CheckSummary
from tests.support import FIXTURES, make_settings

SAMPLE = FIXTURES / "cases" / "aewv-sample"
SCENARIO = FIXTURES / "llm" / "aewv_sample.json"
EXPECTED: dict[str, Any] = json.loads((SAMPLE / "expected.json").read_text())
NOW = datetime(2026, 10, 24, 3, 0, tzinfo=UTC)
LIMITS = store.CaseLimits(max_documents=100, max_file_bytes=20 * 1024 * 1024)


def _settings(home: Path, cases_dir: Path, scenario: Path = SCENARIO) -> Settings:
    return make_settings(
        home,
        cases_dir,
        llm_vendor="fake",
        fake_scenario=scenario,
        task_queue=f"test-{uuid.uuid4()}",
    )


def _upload_sample(cases_dir: Path, case_id: str = "C1", data_class: str = "synthetic") -> None:
    store.create_case(cases_dir, case_id, "AEWV sample", data_class, NOW)  # pyright: ignore[reportArgumentType]
    for name in EXPECTED["upload_order"]:
        stem = name.rsplit(".", 1)[0]
        store.add_document(
            cases_dir, case_id, stem, name, (SAMPLE / name).read_bytes(), NOW, LIMITS
        )


async def _run(
    env: WorkflowEnvironment, settings: Settings, check: CheckInput
) -> tuple[CheckSummary, WorkflowHistory]:
    client: Client = env.client
    llm = build_client(settings, env={})
    async with build_worker(settings, client, llm):
        handle = await client.start_workflow(
            CaseCheckWorkflow.run,
            check,
            id=f"check-{check.check_id}-{uuid.uuid4()}",
            task_queue=settings.task_queue,
        )
        summary = await handle.result()
        history = await handle.fetch_history()
    return summary, history


async def _replay(history: WorkflowHistory) -> None:
    await Replayer(workflows=WORKFLOWS, data_converter=pydantic_data_converter).replay_workflow(
        history
    )


async def test_consistency_check_on_the_sample(
    env: WorkflowEnvironment, home: Path, cases_dir: Path
) -> None:
    _upload_sample(cases_dir)
    check = CheckInput(check_id="K1", case_id="C1", kind="consistency")
    summary, history = await _run(env, _settings(home, cases_dir), check)
    assert (summary.status, summary.conflicts, summary.gaps, summary.clean) == (
        "completed",
        2,
        1,
        False,
    )
    result = store.read_result(cases_dir, "C1", "K1")
    assert result.coverage.model_dump() == EXPECTED["coverage"]
    assert [
        {
            "finding_id": c.finding_id,
            "fact_ids": c.fact_ids,
            "origin": c.origin,
            "drafted_by": c.drafted_by,
        }
        for c in result.conflicts
    ] == EXPECTED["conflicts"]
    assert result.conflicts[1].question.startswith("The questionnaire gives March 2022")
    assert result.conflicts[0].question == (
        "questionnaire.pdf (page 1) gives since 01/2021; application-form.pdf (page 1) gives "
        "from January 2021; tenancy.pdf (page 1) gives from 1 May 2021. Which is correct?"
    )
    assert [
        {"finding_id": g.finding_id, "doc_id": g.doc_id, "kind": g.kind, "pages": g.pages}
        for g in result.gaps
    ] == EXPECTED["gaps"]
    assert [f.fact_id for f in result.facts] == [f"f{n}" for n in range(1, 15)]
    assert (result.error, result.dropped, result.wording_replacements) == (None, [], 0)
    assert [c.role for c in result.calls].count("document.transcribe") == 2
    assert {c.prompt_version for c in result.calls} == {"1"}
    passport = store.read_page(cases_dir, "C1", "passport-scan", 1)
    assert (passport.method, passport.model) == ("transcribed", "anthropic/claude-sonnet-5.5")
    assert "Passport no: XS0000001" in passport.text
    letter = store.read_page(cases_dir, "C1", "employer-letter", 1)
    assert letter.method == "text"
    assert "as Warehouse Supervisor\nsince 1 June 2022." in letter.text
    await _replay(history)


async def test_presubmission_check_on_the_sample(
    env: WorkflowEnvironment, home: Path, cases_dir: Path
) -> None:
    _upload_sample(cases_dir)
    check = CheckInput(
        check_id="K2", case_id="C1", kind="presubmission", checklist_skill="presubmission-aewv"
    )
    summary, history = await _run(env, _settings(home, cases_dir), check)
    assert (summary.status, summary.checked, summary.pending, summary.unable, summary.gaps) == (
        "completed",
        3,
        4,
        1,
        1,
    )
    result = store.read_result(cases_dir, "C1", "K2")
    assert [[i.finding_id, i.item_id, i.status, i.downgraded] for i in result.items] == EXPECTED[
        "items"
    ]
    assert result.checklist is not None
    assert (result.checklist.skill, result.checklist.version) == (
        "presubmission-aewv",
        "0.1-sample",
    )
    assert [g.doc_id for g in result.gaps] == ["unreadable-photo"]
    await _replay(history)


async def test_second_check_reuses_ingested_pages(
    env: WorkflowEnvironment, home: Path, cases_dir: Path
) -> None:
    _upload_sample(cases_dir)
    settings = _settings(home, cases_dir)
    await _run(env, settings, CheckInput(check_id="K1", case_id="C1", kind="consistency"))
    await _run(env, settings, CheckInput(check_id="K3", case_id="C1", kind="consistency"))
    second = store.read_result(cases_dir, "C1", "K3")
    assert [c.role for c in second.calls].count("document.transcribe") == 0
    assert [c.fact_ids for c in second.conflicts] == [c["fact_ids"] for c in EXPECTED["conflicts"]]


def _scenario(tmp_path: Path, edit: Any) -> Path:
    entries = json.loads(SCENARIO.read_text())
    edit(entries)
    path = tmp_path / "scenario.json"
    path.write_text(json.dumps(entries))
    return path


async def test_failed_extraction_is_a_gap_not_silence(
    env: WorkflowEnvironment, home: Path, cases_dir: Path, tmp_path: Path
) -> None:
    def break_tenancy(entries: list[dict[str, Any]]) -> None:
        for entry in entries:
            if entry["match"] == "Document: tenancy.pdf":
                entry["reply"] = {"error": "vendor said no", "retryable": False}

    _upload_sample(cases_dir)
    settings = _settings(home, cases_dir, _scenario(tmp_path, break_tenancy))
    summary, history = await _run(
        env, settings, CheckInput(check_id="K4", case_id="C1", kind="consistency")
    )
    result = store.read_result(cases_dir, "C1", "K4")
    assert summary.status == "completed"
    assert [(g.doc_id, g.kind, g.reason) for g in result.gaps] == [
        ("tenancy", "failed", "fact extraction failed: vendor said no"),
        ("unreadable-photo", "unreadable", "unreadable-photo.jpg: 1 page(s) could not be read"),
    ]
    # Without the tenancy facts the address conflict disappears; the job start one remains.
    assert [c.fact_ids for c in result.conflicts] == [["f4", "f6", "f11"]]
    await _replay(history)


async def test_model_comparison_failure_keeps_the_rule_baseline(
    env: WorkflowEnvironment, home: Path, cases_dir: Path, tmp_path: Path
) -> None:
    def break_compare(entries: list[dict[str, Any]]) -> None:
        for entry in entries:
            if entry["role"] == "case.compare_facts":
                entry["reply"] = {"error": "overloaded", "retryable": False}

    _upload_sample(cases_dir)
    settings = _settings(home, cases_dir, _scenario(tmp_path, break_compare))
    await _run(env, settings, CheckInput(check_id="K5", case_id="C1", kind="consistency"))
    result = store.read_result(cases_dir, "C1", "K5")
    assert result.error == "model comparison skipped, rule baseline only: overloaded"
    assert [(c.fact_ids, c.origin) for c in result.conflicts] == [
        (["f3", "f10", "f14"], ["rule"]),
        (["f4", "f6", "f11"], ["rule"]),
    ]


async def test_failed_item_batch_marks_its_items_unable(
    env: WorkflowEnvironment, home: Path, cases_dir: Path, tmp_path: Path
) -> None:
    def break_batch(entries: list[dict[str, Any]]) -> None:
        for entry in entries:
            if entry["match"] == "- referenced-attachments-exist:":
                entry["reply"] = {"error": "timeout", "retryable": False}

    _upload_sample(cases_dir)
    settings = _settings(home, cases_dir, _scenario(tmp_path, break_batch))
    check = CheckInput(
        check_id="K6", case_id="C1", kind="presubmission", checklist_skill="presubmission-aewv"
    )
    await _run(env, settings, check)
    result = store.read_result(cases_dir, "C1", "K6")
    assert [(i.item_id, i.status, i.downgraded) for i in result.items[5:]] == [
        ("referenced-attachments-exist", "unable", "call_failed"),
        ("police-certificates", "unable", "call_failed"),
        ("client-promised-documents", "unable", "call_failed"),
    ]


async def test_client_data_is_refused_by_the_gate(
    env: WorkflowEnvironment, home: Path, cases_dir: Path
) -> None:
    _upload_sample(cases_dir, data_class="client")
    settings = _settings(home, cases_dir)
    check = CheckInput(check_id="K7", case_id="C1", kind="consistency")
    client = env.client
    llm = build_client(settings, env={})
    # As if roles.toml pointed at the gateway; the gate must refuse before any model call.
    llm.roles = {r: cfg.model_copy(update={"vendor": "gateway"}) for r, cfg in llm.roles.items()}
    async with build_worker(settings, client, llm):
        summary = await client.execute_workflow(
            CaseCheckWorkflow.run, check, id=f"gate-{uuid.uuid4()}", task_queue=settings.task_queue
        )
    assert summary.status == "failed"
    assert summary.error is not None
    assert summary.error.startswith("client data may only go to allow-listed vendors")
    result: CheckResult = store.read_result(cases_dir, "C1", "K7")
    assert (result.status, result.conflicts, result.items) == ("failed", [], [])
    assert store.load_manifest(cases_dir, "C1").documents[0].status == "pending"  # nothing read
