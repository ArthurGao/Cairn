"""AgentRunWorkflow end to end (design §6): tools, write-back validation, run record, usage."""

import json
import uuid
from datetime import timedelta
from pathlib import Path
from typing import Any

from temporalio.client import Client
from temporalio.testing import WorkflowEnvironment

from cairn.activities.agent import AgentActivities
from cairn.core.formats import parse_memory
from cairn.core.index import indexed_slugs, read_index
from cairn.core.tokens import estimate_tokens
from cairn.core.usage import load_usage
from cairn.core.writer import read_changelog
from cairn.llm.client import build_client
from cairn.llm.types import ToolUsePart
from cairn.settings import Settings
from cairn.worker import build_worker
from cairn.workflows.agent_run import AgentRunWorkflow
from cairn.workflows.run_models import RunInput, RunState
from tests.support import FIXTURES, make_settings
from tests.workflows.test_case_check import _replay

SCENARIO = FIXTURES / "llm" / "agent_run.json"
TASK = (
    "Draft a short cover note for the AEWV synthetic case. "
    "Note: the adviser says always write dates as 24 October 2026 in cover notes."
)


def _settings(home: Path, cases_dir: Path, scenario: Path = SCENARIO) -> Settings:
    return make_settings(
        home, cases_dir, llm_vendor="fake", fake_scenario=scenario, task_queue=f"run-{uuid.uuid4()}"
    )


async def _run(env: WorkflowEnvironment, settings: Settings, run: RunInput) -> tuple[RunState, Any]:
    client: Client = env.client
    async with build_worker(settings, client, build_client(settings, env={})):
        handle = await client.start_workflow(
            AgentRunWorkflow.run,
            run,
            id=f"run-{run.run_id}-{uuid.uuid4()}",
            task_queue=settings.task_queue,
        )
        state = await handle.result()
        history = await handle.fetch_history()
    return state, history


async def test_run_reads_memory_and_writes_back_validated_ops(
    env: WorkflowEnvironment, home: Path, cases_dir: Path
) -> None:
    before_usage = load_usage(home)
    state, history = await _run(env, _settings(home, cases_dir), RunInput(run_id="R1", task=TASK))
    assert (state.status, state.error) == ("completed", None)
    assert state.answer is not None
    assert state.answer.startswith("Draft cover note")
    assert [(s.kind, s.tool, s.arg) for s in state.steps] == [
        ("llm", None, None),
        ("tool", "read_memory", "pilot-scope"),
        ("llm", None, None),
    ]
    assert state.loaded == ["memory:pilot-scope"]
    pilot_text = (FIXTURES / "home/memory/pilot-scope.md").read_text()
    loaded_tokens = estimate_tokens(pilot_text)
    assert ([s.tokens for s in state.steps], state.loaded_tokens) == (
        [None, loaded_tokens, None],
        loaded_tokens,
    )
    assert state.context is not None
    assert (state.context.l0_total, state.context.baseline_all) == (790, 1374)
    assert state.writeback is not None
    assert [(a.op, a.slug) for a in state.writeback.applied] == [
        ("create", "cover-note-dates"),
        ("update", "pilot-scope"),
    ]
    assert [(a.before, a.after is not None) for a in state.writeback.applied] == [
        (None, True),
        (pilot_text, True),
    ]
    assert [(r.index, r.slug, r.code) for r in state.writeback.rejected] == [
        (1, "questions-not-accusations", "duplicate"),
        (2, "client-contact", "personal_data"),
    ]
    created = parse_memory((home / "memory/cover-note-dates.md").read_text())
    assert (created.meta()["source_run"], str(created.meta()["created"])) == (
        "R1",
        str(created.meta()["updated"]),
    )
    updated = parse_memory((home / "memory/pilot-scope.md").read_text())
    assert (str(updated.meta()["created"]), updated.meta()["source_run"]) == ("2026-10-01", "R1")
    assert "cover-note-dates" in indexed_slugs(read_index(home))
    assert [(e.op, e.slug, e.actor) for e in read_changelog(home)] == [
        ("create", "cover-note-dates", "run:R1"),
        ("update", "pilot-scope", "run:R1"),
    ]
    [record] = list((home / "state/runs").glob("*-R1.md"))
    text = record.read_text()
    assert "status: completed" in text
    assert f"  loaded: {loaded_tokens}\n" in text
    assert "## Outcome\nDrafted a cover note for the synthetic AEWV case." in text
    assert "- Confirm the employer's address" in text
    usage = load_usage(home)
    assert usage["pilot-scope"].reads == before_usage["pilot-scope"].reads + 1
    assert usage["pilot-scope"].written_by_runs == 1
    assert usage["cover-note-dates"].written_by_runs == 1
    await _replay(history)


def _scenario(tmp_path: Path, entries: list[dict[str, Any]]) -> Path:
    path = tmp_path / "scenario.json"
    path.write_text(json.dumps(entries))
    return path


async def test_max_steps_fails_without_write_back(
    env: WorkflowEnvironment, home: Path, cases_dir: Path, tmp_path: Path
) -> None:
    loop = [
        {
            "role": "agent.main",
            "repeat": True,
            "reply": {
                "tool_calls": [
                    {"id": "t", "name": "load_skill", "args": {"name": "presubmission-aewv"}}
                ],
                "stop_reason": "tool_use",
            },
        }
    ]
    settings = _settings(home, cases_dir, _scenario(tmp_path, loop))
    state, history = await _run(env, settings, RunInput(run_id="R2", task="loop", max_steps=2))
    assert (state.status, state.error, state.writeback) == ("failed", "max_steps reached", None)
    assert [s.kind for s in state.steps] == ["llm", "tool", "llm", "tool"]
    assert state.loaded == ["skill:presubmission-aewv"]
    assert read_changelog(home) == []
    [record] = list((home / "state/runs").glob("*-R2.md"))
    assert "status: failed" in record.read_text()
    await _replay(history)


async def test_failed_extraction_is_reported_not_silent(
    env: WorkflowEnvironment, home: Path, cases_dir: Path, tmp_path: Path
) -> None:
    entries = [
        {"role": "agent.main", "reply": {"text": "Done."}},
        {"role": "memory.extract", "reply": {"error": "overloaded", "retryable": False}},
    ]
    state, _ = await _run(
        env,
        _settings(home, cases_dir, _scenario(tmp_path, entries)),
        RunInput(run_id="R3", task="hi"),
    )
    assert (state.status, state.answer) == ("completed", "Done.")
    assert state.writeback is not None
    assert (state.writeback.applied, state.writeback.error) == (
        [],
        "memory extraction failed: overloaded",
    )


async def test_rate_limited_model_calls_wait_the_vendors_delay_and_keep_retrying(
    env: WorkflowEnvironment, home: Path, cases_dir: Path, tmp_path: Path
) -> None:
    limited = {"error": "rate limited", "retryable": True, "retry_after": 29}
    entries = [
        *[{"role": "agent.main", "reply": limited}] * 4,
        {"role": "agent.main", "reply": {"text": "Done."}},
        {"role": "memory.extract", "reply": {"error": "overloaded", "retryable": False}},
    ]
    state, history = await _run(
        env,
        _settings(home, cases_dir, _scenario(tmp_path, entries)),
        RunInput(run_id="R4", task="hi"),
    )
    assert (state.status, state.answer) == ("completed", "Done.")
    # Failed attempts are not history events, so the wait shows as the time between the model
    # step's scheduling and its completion: 4 x 29 s, where the backoff alone is 2+4+8+16 s.
    scheduled = next(
        e
        for e in history.events
        if e.activity_task_scheduled_event_attributes.activity_type.name == "agent_step"
    )
    completed = next(
        e
        for e in history.events
        if e.activity_task_completed_event_attributes.scheduled_event_id == scheduled.event_id
    )
    waited = completed.event_time.ToDatetime() - scheduled.event_time.ToDatetime()
    assert timedelta(seconds=116) <= waited < timedelta(seconds=146)
    await _replay(history)


async def test_tools_refuse_paths_outside_the_skill(
    home: Path, cases_dir: Path, tmp_path: Path
) -> None:
    settings = _settings(home, cases_dir, _scenario(tmp_path, []))
    acts = AgentActivities(settings, build_client(settings, env={}))

    async def tool(tool_name: str, **args: str) -> tuple[bool, str]:
        out = await acts.run_tool(ToolUsePart(id="t", name=tool_name, args=args))
        return out.error, out.content

    escape = await tool("read_skill_file", name="presubmission-aewv", path="../../AGENTS.md")
    assert escape == (True, "error: ../../AGENTS.md is not a file inside skill presubmission-aewv")
    assert await tool("read_memory", slug="../AGENTS") == (
        True,
        "error: '../AGENTS' is not a valid memory slug",
    )
    ok, content = await tool(
        "read_skill_file", name="presubmission-aewv", path="references/checklist.yaml"
    )
    assert (ok, content.startswith("# SAMPLE CHECKLIST")) == (False, True)
    assert await tool("delete_memory", name="x") == (True, "error: no skill x")
