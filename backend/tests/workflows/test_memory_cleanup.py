"""MemoryCleanupWorkflow (design §7) on the time-skipping server: wait, expire, approve,
reject, conflict, mechanical index sync and refused drafts. Each history is replayed."""

import asyncio
import json
import uuid
from datetime import date, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from temporalio.client import Client, WorkflowHandle
from temporalio.testing import WorkflowEnvironment

from cairn.core.consolidate import MergeDraft
from cairn.core.index import archive_path, index_current, memory_path
from cairn.core.writer import read_changelog
from cairn.llm.client import build_client
from cairn.settings import Settings
from cairn.worker import build_worker
from cairn.workflows.cleanup_models import CleanupInput, CleanupState, ReviewDecision
from cairn.workflows.memory_cleanup import MemoryCleanupWorkflow
from tests.support import FIXTURES, make_settings
from tests.workflows.test_case_check import _replay

SCENARIO = FIXTURES / "llm" / "cleanup.json"
TZ = ZoneInfo("Pacific/Auckland")
TARGET, MEMBER, STALE = (
    "conflicts-as-questions",
    "neutral-wording-for-discrepancies",
    "intake-form-v1-dates",
)
Handle = WorkflowHandle[MemoryCleanupWorkflow, CleanupState]


def _settings(home: Path, cases_dir: Path, scenario: Path = SCENARIO) -> Settings:
    return make_settings(
        home, cases_dir, llm_vendor="fake", fake_scenario=scenario, task_queue=f"c-{uuid.uuid4()}"
    )


async def _usage_relative_to_today(env: WorkflowEnvironment, home: Path) -> None:
    """Usage dates follow the test server's clock (which earlier expiry tests moved on), so
    'stale' means the same thing on every run."""
    path = home / "state/usage.json"
    usage = json.loads(path.read_text())
    today = (await env.get_current_time()).astimezone(TZ).date()
    for slug, entry in usage.items():
        days = 200 if slug == STALE else 10
        entry["last_read"] = (today - timedelta(days=days)).isoformat()
    path.write_text(json.dumps(usage))


async def _until(handle: Handle, status: str) -> CleanupState:
    for _ in range(400):
        state = await handle.query(MemoryCleanupWorkflow.get_state)
        if state is not None and state.status == status:
            return state
        await asyncio.sleep(0.02)
    raise AssertionError(f"the cleanup never reached {status}")


async def _cleanup(
    env: WorkflowEnvironment,
    settings: Settings,
    decide: Any = None,
    config: CleanupInput | None = None,
) -> tuple[CleanupState, CleanupState | None, Any]:
    """Run one cleanup; `decide(handle, proposal_state)` acts during the review wait."""
    client: Client = env.client
    async with build_worker(settings, client, build_client(settings, env={})):
        handle = await client.start_workflow(
            MemoryCleanupWorkflow.run,
            config or CleanupInput(),
            id=f"cleanup-{uuid.uuid4()}",
            task_queue=settings.task_queue,
        )
        waiting = None
        if decide is not None:
            waiting = await _until(handle, "awaiting_review")
            await decide(handle, waiting)
        state = await handle.result()
        history = await handle.fetch_history()
    await _replay(history)
    return state, waiting, history


def _approve(*op_ids: str) -> Any:
    async def decide(handle: Handle, _: CleanupState) -> None:
        await handle.signal(
            MemoryCleanupWorkflow.submit_review, ReviewDecision(approved_op_ids=list(op_ids))
        )

    return decide


async def test_approved_changes_are_applied_as_one_merge_and_one_archive(
    env: WorkflowEnvironment, home: Path, cases_dir: Path
) -> None:
    await _usage_relative_to_today(env, home)
    target_before = memory_path(home, TARGET).read_text()
    member_before = memory_path(home, MEMBER).read_text()
    state, waiting, _ = await _cleanup(
        env, _settings(home, cases_dir), _approve(f"archive:{STALE}", f"merge:{TARGET}")
    )
    assert waiting is not None
    assert waiting.proposal is not None
    assert [(c.op_id, c.kind, [f.slug for f in c.changes]) for c in waiting.proposal.changes] == [
        (f"archive:{STALE}", "archive", [STALE]),
        (f"merge:{TARGET}", "merge", [TARGET, MEMBER]),
    ]
    merge = waiting.proposal.changes[1]
    assert [(c.slug, c.before, c.after is None) for c in merge.changes] == [
        (TARGET, target_before, False),
        (MEMBER, member_before, True),
    ]
    assert [f.check for f in waiting.proposal.findings] == ["duplicate", "stale"]
    assert waiting.proposal.mechanical == []
    assert waiting.expires is not None
    assert waiting.started is not None
    # The deadline is set when the wait starts, after the lint and draft activities.
    assert timedelta(days=6) <= waiting.expires - waiting.started < timedelta(days=6, minutes=1)

    assert state.status == "applied"
    assert state.outcome is not None
    assert state.outcome.applied == [f"archive:{STALE}", f"merge:{TARGET}"]
    assert state.outcome.rejected == []
    log = read_changelog(home)
    assert [(e.op, e.slug, e.actor) for e in log] == [
        ("archive", STALE, f"cleanup:{state.workflow_id}"),
        ("update", TARGET, f"cleanup:{state.workflow_id}"),
        ("archive", MEMBER, f"cleanup:{state.workflow_id}"),
    ]
    assert archive_path(home, STALE).is_file()
    assert not memory_path(home, STALE).exists()
    assert archive_path(home, MEMBER).is_file()
    assert not memory_path(home, MEMBER).exists()
    draft = MergeDraft.model_validate(json.loads(SCENARIO.read_text())[0]["reply"]["data"])
    applied_day: date = log[1].at.astimezone(TZ).date()
    merged = memory_path(home, TARGET).read_text()
    assert merged == (
        f"---\nname: {TARGET}\ndescription: {draft.description}\nmetadata:\n  type: feedback\n"
        f"  created: 2026-07-14\n  updated: {applied_day.isoformat()}\n---\n\n{draft.body}"
    )
    assert index_current(home)[0]


async def test_only_approved_changes_are_applied(
    env: WorkflowEnvironment, home: Path, cases_dir: Path
) -> None:
    await _usage_relative_to_today(env, home)
    state, _, _ = await _cleanup(env, _settings(home, cases_dir), _approve(f"merge:{TARGET}"))
    assert state.outcome is not None
    assert state.outcome.applied == [f"merge:{TARGET}"]
    assert [(e.op, e.slug) for e in read_changelog(home)] == [
        ("update", TARGET),
        ("archive", MEMBER),
    ]
    assert memory_path(home, STALE).is_file()


async def test_unanswered_proposal_expires_with_nothing_applied(
    env: WorkflowEnvironment, home: Path, cases_dir: Path
) -> None:
    await _usage_relative_to_today(env, home)
    state, _, _ = await _cleanup(env, _settings(home, cases_dir))
    assert (state.status, state.outcome, state.decision) == ("expired", None, None)
    assert read_changelog(home) == []
    assert memory_path(home, STALE).is_file()


async def test_reject_all_applies_nothing(
    env: WorkflowEnvironment, home: Path, cases_dir: Path
) -> None:
    await _usage_relative_to_today(env, home)
    state, _, _ = await _cleanup(env, _settings(home, cases_dir), _approve())
    assert (state.status, state.outcome) == ("rejected", None)
    assert state.decision == ReviewDecision(approved_op_ids=[])
    assert read_changelog(home) == []


async def test_a_file_edited_during_review_rejects_its_whole_merge(
    env: WorkflowEnvironment, home: Path, cases_dir: Path
) -> None:
    await _usage_relative_to_today(env, home)
    target_before = memory_path(home, TARGET).read_text()

    async def edit_then_approve(handle: Handle, waiting: CleanupState) -> None:
        member = memory_path(home, MEMBER)
        member.write_text(member.read_text() + "Edited during the review.\n")
        await _approve(f"archive:{STALE}", f"merge:{TARGET}")(handle, waiting)

    state, _, _ = await _cleanup(env, _settings(home, cases_dir), edit_then_approve)
    assert state.status == "applied"
    assert state.outcome is not None
    assert state.outcome.applied == [f"archive:{STALE}"]
    assert [(r.op_id, r.reason) for r in state.outcome.rejected] == [
        (f"merge:{TARGET}", f"{MEMBER}: the file changed")
    ]
    assert memory_path(home, TARGET).read_text() == target_before  # never a half-merge
    assert memory_path(home, MEMBER).read_text().endswith("Edited during the review.\n")
    assert [(e.op, e.slug) for e in read_changelog(home)] == [("archive", STALE)]


async def test_index_drift_is_synced_and_an_unfaithful_draft_becomes_a_finding(
    env: WorkflowEnvironment, home: Path, cases_dir: Path, tmp_path: Path
) -> None:
    await _usage_relative_to_today(env, home)
    index = home / "memory/MEMORY.md"
    index.write_text(
        "".join(line for line in index.read_text().splitlines(True) if STALE not in line)
    )
    scenario = json.loads(SCENARIO.read_text())
    scenario[0]["reply"]["data"]["body"] += "Reply within 14 days.\n"
    unfaithful = tmp_path / "unfaithful.json"
    unfaithful.write_text(json.dumps(scenario))
    state, waiting, _ = await _cleanup(
        env, _settings(home, cases_dir, unfaithful), _approve(f"archive:{STALE}")
    )
    assert waiting is not None
    assert waiting.proposal is not None
    assert [c.op_id for c in waiting.proposal.changes] == [f"archive:{STALE}"]
    refused = [f for f in waiting.proposal.findings if f.check == "merge_not_drafted"]
    assert [(f.slugs, f.message) for f in refused] == [
        (
            [TARGET, MEMBER],
            "could not draft a faithful merge: the merged body adds '14', which no source has",
        )
    ]
    [sync] = waiting.proposal.mechanical
    assert next((e.id, e.op) for e in read_changelog(home)) == (sync, "index_sync")
    assert state.status == "applied"


async def test_nothing_to_review_finishes_without_waiting(
    env: WorkflowEnvironment, home: Path, cases_dir: Path
) -> None:
    await _usage_relative_to_today(env, home)
    quiet = CleanupInput(stale_days=1_000, dup_threshold=1.01, dup_body_threshold=1.01)
    state, _, _ = await _cleanup(env, _settings(home, cases_dir), config=quiet)
    assert (state.status, state.expires) == ("no_changes", None)
    assert state.proposal is not None
    assert state.proposal.changes == []


async def test_a_decision_outside_the_review_wait_is_ignored(
    env: WorkflowEnvironment, home: Path, cases_dir: Path
) -> None:
    await _usage_relative_to_today(env, home)

    async def twice(handle: Handle, waiting: CleanupState) -> None:
        await _approve()(handle, waiting)
        await _approve(f"archive:{STALE}")(handle, waiting)  # a second decision

    state, _, _ = await _cleanup(env, _settings(home, cases_dir), twice)
    assert (state.status, read_changelog(home)) == ("rejected", [])
