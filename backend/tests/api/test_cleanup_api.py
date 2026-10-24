"""Cleanup API (design §7.1, §11) on a real local Temporal server, which has Schedules: ensure,
trigger, single flight, review validation, approve, and the archived file's effect."""

import asyncio
import contextlib
import json
import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import httpx
import pytest
from temporalio.client import Client
from temporalio.service import RPCError
from temporalio.testing import WorkflowEnvironment

from cairn.api.app import create_app
from cairn.llm.client import build_client
from cairn.schedule import ensure_schedule
from cairn.settings import Settings
from cairn.worker import build_worker
from cairn.workflows.cleanup_models import SCHEDULE_ID
from tests.support import FIXTURES, make_settings

STALE = "intake-form-v1-dates"


@pytest.fixture
def settings(home: Path, cases_dir: Path, temporal_env: WorkflowEnvironment) -> Settings:
    usage_path = home / "state/usage.json"
    usage = json.loads(usage_path.read_text())
    today = datetime.now(ZoneInfo("Pacific/Auckland")).date()
    for slug, entry in usage.items():
        entry["last_read"] = (today - timedelta(days=200 if slug == STALE else 10)).isoformat()
    usage_path.write_text(json.dumps(usage))
    return make_settings(
        home,
        cases_dir,
        temporal_address=temporal_env.client.service_client.config.target_host,
        llm_vendor="fake",
        fake_scenario=FIXTURES / "llm" / "cleanup.json",
        task_queue=f"cleanup-{uuid.uuid4()}",
    )


async def _drop_schedule(client: Client) -> None:
    with contextlib.suppress(RPCError):
        await client.get_schedule_handle(SCHEDULE_ID).delete()


@pytest.fixture
async def api(
    settings: Settings, temporal_env: WorkflowEnvironment
) -> AsyncIterator[httpx.AsyncClient]:
    await _drop_schedule(temporal_env.client)
    app = create_app(settings)
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=transport, base_url="http://test") as client,
    ):
        yield client
    await _drop_schedule(temporal_env.client)


async def _poll(api: httpx.AsyncClient, path: str, done: Any) -> Any:
    for _ in range(300):
        response = await api.get(path)
        if response.status_code == 200 and (body := response.json()) and done(body):
            return body
        await asyncio.sleep(0.05)
    raise AssertionError(f"{path} never got there")


async def test_trigger_without_a_schedule_is_503(api: httpx.AsyncClient) -> None:
    response = await api.post("/api/cleanup/run")
    assert (response.status_code, response.json()["error"]["code"]) == (503, "schedule_missing")


async def test_unknown_cleanup_is_404(api: httpx.AsyncClient) -> None:
    for workflow_id in ("cleanup-nope", "run-01ABC"):
        response = await api.get(f"/api/cleanup/{workflow_id}")
        assert (response.status_code, response.json()["error"]["code"]) == (
            404,
            "cleanup_not_found",
        )


async def test_trigger_review_and_approve(
    api: httpx.AsyncClient, settings: Settings, temporal_env: WorkflowEnvironment, home: Path
) -> None:
    client = temporal_env.client
    assert await ensure_schedule(client, settings) == "created"
    assert await ensure_schedule(client, settings) == "updated"
    async with build_worker(settings, client, build_client(settings, env={})):
        assert (await api.post("/api/cleanup/run")).status_code == 202
        [brief] = await _poll(
            api, "/api/cleanup", lambda b: len(b) == 1 and b[0]["status"] == "awaiting_review"
        )
        assert brief["changes"] == 2
        wf_id = brief["workflow_id"]
        again = await api.post("/api/cleanup/run")
        assert (again.status_code, again.json()["error"]["code"]) == (409, "cleanup_in_progress")
        assert wf_id in again.json()["error"]["message"]

        proposal = (await api.get(f"/api/cleanup/{wf_id}")).json()["proposal"]
        assert [c["op_id"] for c in proposal["changes"]] == [
            f"archive:{STALE}",
            "merge:conflicts-as-questions",
        ]
        unknown = await api.post(f"/api/cleanup/{wf_id}/review", json={"approved_op_ids": ["x"]})
        assert (unknown.status_code, unknown.json()["error"]["code"]) == (422, "unknown_op")
        ok = await api.post(
            f"/api/cleanup/{wf_id}/review",
            json={"approved_op_ids": [f"archive:{STALE}"], "reviewer": "E2E"},
        )
        assert ok.status_code == 202
        state = await _poll(api, f"/api/cleanup/{wf_id}", lambda s: s["status"] == "applied")
        [after] = (await api.get("/api/cleanup")).json()
        assert (after["status"], after["changes"], after["expires"] is not None) == (
            "applied",
            2,
            True,
        )
        late = await api.post(f"/api/cleanup/{wf_id}/review", json={"approved_op_ids": []})
        assert (late.status_code, late.json()["error"]["code"]) == (409, "not_awaiting_review")

    assert state["outcome"]["applied"] == [f"archive:{STALE}"]
    assert state["decision"]["reviewer"] == "E2E"
    assert (home / f"memory/_archive/{STALE}.md").is_file()
    slugs = [e["slug"] for e in (await api.get("/api/memory")).json()["entries"]]
    assert STALE not in slugs
    assert "neutral-wording-for-discrepancies" in slugs  # the merge was not approved
