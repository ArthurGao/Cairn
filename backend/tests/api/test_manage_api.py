"""Manage API (design §11): runs, context preview, memory with undo, skills."""

import asyncio
import uuid
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from temporalio.testing import WorkflowEnvironment

from cairn.api.app import create_app
from cairn.core.tokens import estimate_tokens
from cairn.llm.client import build_client
from cairn.settings import Settings
from cairn.worker import build_worker
from tests.support import FIXTURES, make_settings
from tests.workflows.test_agent_run import TASK


@pytest.fixture
def settings(home: Path, cases_dir: Path, temporal_env: WorkflowEnvironment) -> Settings:
    return make_settings(
        home,
        cases_dir,
        temporal_address=temporal_env.client.service_client.config.target_host,
        llm_vendor="fake",
        fake_scenario=FIXTURES / "llm" / "agent_run.json",
        task_queue=f"manage-{uuid.uuid4()}",
    )


@pytest.fixture
async def api(settings: Settings) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app(settings)
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=transport, base_url="http://test") as client,
    ):
        yield client


async def test_memory_list_detail_and_budget(api: httpx.AsyncClient) -> None:
    body = (await api.get("/api/memory")).json()
    assert [(e["slug"], e["type"]) for e in body["entries"]] == [
        ("adviser-wants-english-findings", "user"),
        ("conflicts-as-questions", "feedback"),
        ("neutral-wording-for-discrepancies", "feedback"),
        ("pilot-scope", "project"),
        ("checklist-owner", "reference"),
        ("intake-form-v1-dates", "reference"),
    ]
    assert body["entries"][0]["usage"] == {
        "reads": 14,
        "last_read": "2026-10-21",
        "written_by_runs": 0,
    }
    golden = estimate_tokens((FIXTURES / "home/memory/MEMORY.md").read_text())
    assert body["budget"] == {"tokens": golden, "budget": 1500, "over": False}
    detail = (await api.get("/api/memory/pilot-scope")).json()
    assert (detail["body"].startswith("The pilot runs"), detail["changelog"]) == (True, [])
    missing = await api.get("/api/memory/nope")
    assert (missing.status_code, missing.json()["error"]["code"]) == (404, "memory_not_found")


async def test_context_preview_and_skills(api: httpx.AsyncClient) -> None:
    preview = (await api.get("/api/context/preview")).json()
    assert (preview["breakdown"]["l0_total"], preview["breakdown"]["baseline_all"]) == (790, 1374)
    skills = (await api.get("/api/skills")).json()
    assert [(s["name"], s["read_only"], [r["path"] for r in s["references"]]) for s in skills] == [
        ("case-consistency-check", False, ["references/fact-categories.md"]),
        ("presubmission-aewv", False, ["references/checklist.yaml"]),
    ]
    detail = (await api.get("/api/skills/presubmission-aewv")).json()
    assert detail["body"].startswith("# Pre-submission check")


async def _wait(api: httpx.AsyncClient, run_id: str) -> dict[str, Any]:
    for _ in range(200):
        state = (await api.get(f"/api/runs/{run_id}")).json()
        if state["status"] in ("completed", "failed"):
            return state
        await asyncio.sleep(0.05)
    raise AssertionError("run did not finish")


async def test_run_write_back_and_undo(
    api: httpx.AsyncClient, settings: Settings, temporal_env: WorkflowEnvironment, home: Path
) -> None:
    async with build_worker(settings, temporal_env.client, build_client(settings, env={})):
        started = await api.post("/api/runs", json={"task": TASK})
        assert started.status_code == 202
        run_id = started.json()["run_id"]
        state = await _wait(api, run_id)
    assert state["status"] == "completed"
    assert [a["slug"] for a in state["writeback"]["applied"]] == ["cover-note-dates", "pilot-scope"]
    runs = (await api.get("/api/runs")).json()
    assert [(r["run_id"], r["status"], r["task"]) for r in runs if r["run_id"] == run_id] == [
        (run_id, "completed", TASK)
    ]
    log = (await api.get("/api/memory/changelog")).json()
    assert [e["slug"] for e in log] == ["pilot-scope", "cover-note-dates"]  # newest first
    create_id = log[1]["id"]
    undone = await api.post(f"/api/memory/changelog/{create_id}/undo")
    assert undone.status_code == 200
    assert [(e["op"], e["slug"], e["undo_of"]) for e in undone.json()] == [
        ("archive", "cover-note-dates", create_id)
    ]
    assert not (home / "memory/cover-note-dates.md").exists()
    after_undo = (await api.get(f"/api/runs/{run_id}")).json()["writeback"]["applied"]
    assert [(a["slug"], a["undone"]) for a in after_undo] == [
        ("cover-note-dates", True),
        ("pilot-scope", False),
    ]
    assert "cover-note-dates" not in [
        e["slug"] for e in (await api.get("/api/memory")).json()["entries"]
    ]
    again = await api.post(f"/api/memory/changelog/{create_id}/undo")
    assert again.json() == []  # already undone: nothing applied twice
    missing = await api.post("/api/memory/changelog/chg_nope/undo")
    assert (missing.status_code, missing.json()["error"]["code"]) == (404, "change_not_found")


async def test_unknown_run_is_404(api: httpx.AsyncClient) -> None:
    response = await api.get("/api/runs/01NORUN")
    assert (response.status_code, response.json()["error"]["code"]) == (404, "run_not_found")
