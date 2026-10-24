"""Case API (design §11) against a real local Temporal server and a worker on the fake vendor."""

import asyncio
import uuid
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from temporalio.testing import WorkflowEnvironment

from cairn.api.app import create_app
from cairn.llm.client import build_client
from cairn.settings import Settings
from cairn.worker import build_worker
from tests.support import FIXTURES, make_settings

SAMPLE = FIXTURES / "cases" / "aewv-sample"
SCENARIO = FIXTURES / "llm" / "aewv_sample.json"


def _address(env: WorkflowEnvironment) -> str:
    return env.client.service_client.config.target_host


@pytest.fixture
def settings(home: Path, cases_dir: Path, temporal_env: WorkflowEnvironment) -> Settings:
    return make_settings(
        home,
        cases_dir,
        temporal_address=_address(temporal_env),
        llm_vendor="fake",
        fake_scenario=SCENARIO,
        task_queue=f"api-{uuid.uuid4()}",
        max_upload_mb=1,
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


async def _case(api: httpx.AsyncClient, label: str = "AEWV sample") -> str:
    response = await api.post("/api/cases", json={"label": label})
    assert response.status_code == 201
    return response.json()["case_id"]


async def _upload(api: httpx.AsyncClient, case_id: str, *names: str) -> httpx.Response:
    files = [("files", (name, (SAMPLE / name).read_bytes())) for name in names]
    return await api.post(f"/api/cases/{case_id}/documents", files=files)


async def test_create_list_and_get_cases(api: httpx.AsyncClient) -> None:
    case_id = await _case(api, "  First case  ")
    listed = (await api.get("/api/cases")).json()
    assert [(c["case_id"], c["label"], c["documents"], c["checks"]) for c in listed] == [
        (case_id, "First case", 0, [])
    ]
    detail = (await api.get(f"/api/cases/{case_id}")).json()
    assert (detail["manifest"]["data_class"], detail["checks"]) == ("synthetic", [])
    missing = await api.get("/api/cases/01NOPE")
    assert (missing.status_code, missing.json()["error"]["code"]) == (404, "case_not_found")
    empty = await api.post("/api/cases", json={"label": ""})
    assert (empty.status_code, empty.json()["error"]["code"]) == (422, "invalid_request")


async def test_uploads_are_sniffed_and_limited(api: httpx.AsyncClient) -> None:
    case_id = await _case(api)
    response = await _upload(api, case_id, "employer-letter.pdf", "passport-scan.png")
    assert response.status_code == 201
    assert [(d["filename"], d["media_type"], d["status"]) for d in response.json()] == [
        ("employer-letter.pdf", "application/pdf", "pending"),
        ("passport-scan.png", "image/png", "pending"),
    ]
    bad = await api.post(f"/api/cases/{case_id}/documents", files=[("files", ("x.exe", b"MZ\x90"))])
    assert (bad.status_code, bad.json()["error"]["code"]) == (415, "unsupported_type")
    big = b"%PDF-" + b"0" * (1024 * 1024)
    over = await api.post(f"/api/cases/{case_id}/documents", files=[("files", ("big.pdf", big))])
    assert (over.status_code, over.json()["error"]["code"]) == (413, "case_too_large")
    doc_id = response.json()[0]["doc_id"]
    original = await api.get(f"/api/cases/{case_id}/documents/{doc_id}/original")
    assert original.content == (SAMPLE / "employer-letter.pdf").read_bytes()


async def test_checklists(api: httpx.AsyncClient) -> None:
    [checklist] = (await api.get("/api/checklists")).json()
    assert (
        checklist["skill"],
        checklist["version"],
        len(checklist["items"]),
        checklist["error"],
    ) == (
        "presubmission-aewv",
        "0.1-sample",
        8,
        None,
    )


async def test_start_check_validation(api: httpx.AsyncClient) -> None:
    case_id = await _case(api)
    empty = await api.post(f"/api/cases/{case_id}/checks", json={"kind": "consistency"})
    assert (empty.status_code, empty.json()["error"]["code"]) == (422, "case_empty")
    await _upload(api, case_id, "tenancy.pdf")
    no_list = await api.post(f"/api/cases/{case_id}/checks", json={"kind": "presubmission"})
    assert no_list.json()["error"]["code"] == "checklist_required"
    bad_list = await api.post(
        f"/api/cases/{case_id}/checks",
        json={"kind": "presubmission", "checklist_skill": "presubmission-nope"},
    )
    assert (bad_list.status_code, bad_list.json()["error"]["code"]) == (422, "spec_invalid")


async def _wait_done(api: httpx.AsyncClient, case_id: str, check_id: str) -> dict[str, Any]:
    for _ in range(200):
        view = (await api.get(f"/api/cases/{case_id}/checks/{check_id}")).json()
        if view["status"] != "running":
            return view
        await asyncio.sleep(0.05)
    raise AssertionError("check did not finish")


async def test_check_review_and_sign_off(
    api: httpx.AsyncClient, settings: Settings, temporal_env: WorkflowEnvironment
) -> None:
    case_id = await _case(api)
    names = [
        "questionnaire.pdf",
        "employer-letter.pdf",
        "application-form.pdf",
        "tenancy.pdf",
        "cover-letter.pdf",
        "passport-scan.png",
        "unreadable-photo.jpg",
    ]
    assert (await _upload(api, case_id, *names)).status_code == 201
    async with build_worker(settings, temporal_env.client, build_client(settings, env={})):
        started = await api.post(f"/api/cases/{case_id}/checks", json={"kind": "consistency"})
        assert started.status_code == 202
        check_id = started.json()["check_id"]
        view = await _wait_done(api, case_id, check_id)
    assert view["status"] == "completed"
    assert [c["fact_ids"] for c in view["result"]["conflicts"]] == [
        ["f3", "f10", "f14"],
        ["f4", "f6", "f11"],
    ]
    assert view["blockers"] == ["c1", "c2", "g1"]
    [brief] = (await api.get(f"/api/cases/{case_id}")).json()["checks"]
    assert (brief["status"], brief["counts"]["conflicts"], brief["counts"]["gaps"]) == (
        "completed",
        2,
        1,
    )

    base = f"/api/cases/{case_id}/checks/{check_id}"
    no_note = await api.post(
        f"{base}/findings/c1/review", json={"action": "dismissed", "adviser": "A. Adviser"}
    )
    assert (no_note.status_code, no_note.json()["error"]["code"]) == (422, "note_required")
    blocked = await api.post(f"{base}/signoff", json={"adviser": "A. Adviser"})
    assert (blocked.status_code, blocked.json()["error"]["message"]) == (
        409,
        "settle these findings first: c1, c2, g1",
    )
    for finding, action, note in [
        ("c1", "dismissed", "Tenancy started after the move; confirmed by phone"),
        ("c2", "confirmed", None),
        ("g1", "confirmed", "Asked the client for a clearer photo"),
    ]:
        reviewed = await api.post(
            f"{base}/findings/{finding}/review",
            json={"action": action, "note": note, "adviser": "A. Adviser"},
        )
        assert reviewed.status_code == 200
    signed = await api.post(f"{base}/signoff", json={"adviser": "A. Adviser"})
    assert signed.status_code == 200
    final = (await api.get(base)).json()
    assert (final["blockers"], final["signed_off"]["adviser"]) == ([], "A. Adviser")
    assert final["review"] == {"c1": "dismissed", "c2": "confirmed", "g1": "confirmed"}
    assert final["notes"]["c1"] == "Tenancy started after the move; confirmed by phone"

    doc_id = view["result"]["facts"][5]["doc_id"]  # employer-letter
    page = (await api.get(f"/api/cases/{case_id}/documents/{doc_id}/pages/1")).json()
    assert (page["method"], "since 1 June 2022." in page["text"]) == ("text", True)
    render = await api.get(f"/api/cases/{case_id}/documents/{doc_id}/pages/1/render")
    assert (render.status_code, render.headers["content-type"], render.content[:4]) == (
        200,
        "image/png",
        b"\x89PNG",
    )


async def test_temporal_down_is_503(home: Path, cases_dir: Path) -> None:
    settings = make_settings(home, cases_dir, temporal_address="127.0.0.1:1")
    app = create_app(settings)
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as api:
        case_id = await _case(api)
        await _upload(api, case_id, "tenancy.pdf")
        response = await api.post(f"/api/cases/{case_id}/checks", json={"kind": "consistency"})
    assert (response.status_code, response.json()["error"]["code"]) == (503, "temporal_unavailable")


async def test_unknown_check_is_404(api: httpx.AsyncClient) -> None:
    case_id = await _case(api)
    response = await api.get(f"/api/cases/{case_id}/checks/01NOCHECK")
    assert (response.status_code, response.json()["error"]["code"]) == (404, "check_not_found")


async def test_upload_request_size_is_capped_before_parsing(api: httpx.AsyncClient) -> None:
    case_id = await _case(api)
    # 1 MB per file and 100 documents per case: a declared body far over the total is refused.
    response = await api.post(
        f"/api/cases/{case_id}/documents",
        content=b"x" * 10,
        headers={
            "content-type": "multipart/form-data; boundary=b",
            "content-length": str(500 * 1024 * 1024),
        },
    )
    assert (response.status_code, response.json()["error"]["code"]) == (413, "case_too_large")


async def test_too_many_files_in_one_request(api: httpx.AsyncClient, settings: Settings) -> None:
    case_id = await _case(api)
    files = [("files", (f"n{i}.md", b"# note")) for i in range(settings.max_documents_per_case + 1)]
    response = await api.post(f"/api/cases/{case_id}/documents", files=files)
    assert (response.status_code, response.json()["error"]["code"]) == (413, "case_too_large")
    assert (await api.get(f"/api/cases/{case_id}")).json()["manifest"]["documents"] == []
