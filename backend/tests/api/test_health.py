from pathlib import Path

import httpx
from fastapi import FastAPI
from temporalio.testing import WorkflowEnvironment

from cairn.api.app import create_app
from tests.support import make_settings

CLOSED_PORT = "127.0.0.1:1"


def _address(env: WorkflowEnvironment) -> str:
    return env.client.service_client.config.target_host


def _client(app: FastAPI) -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


async def _get_health(
    home: Path, cases_dir: Path, temporal_address: str, **overrides: str
) -> httpx.Response:
    app = create_app(make_settings(home, cases_dir, temporal_address=temporal_address, **overrides))
    async with _client(app) as client:
        return await client.get("/api/health")


async def test_health_ok(home: Path, cases_dir: Path, temporal_env: WorkflowEnvironment) -> None:
    response = await _get_health(home, cases_dir, _address(temporal_env))
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "data_class": "synthetic",
        "temporal": "ok",
        "home": str(home),
        "cases": str(cases_dir),
        "build": "",
    }


async def test_health_names_the_deployed_build(
    home: Path, cases_dir: Path, temporal_env: WorkflowEnvironment
) -> None:
    response = await _get_health(
        home,
        cases_dir,
        _address(temporal_env),
        build_sha="1d88ff5560128a72683ce07cd23879d70d95c218",
    )
    assert response.status_code == 200
    assert response.json()["build"] == "1d88ff5560128a72683ce07cd23879d70d95c218"


async def test_health_503_when_temporal_unreachable(home: Path, cases_dir: Path) -> None:
    response = await _get_health(home, cases_dir, CLOSED_PORT)
    assert response.status_code == 503
    error = response.json()["error"]
    assert error["code"] == "unhealthy"
    assert error["message"].startswith(f"temporal: unreachable at {CLOSED_PORT} (")


async def test_health_503_names_missing_home_file(
    home: Path, cases_dir: Path, temporal_env: WorkflowEnvironment
) -> None:
    (home / "AGENTS.md").unlink()
    response = await _get_health(home, cases_dir, _address(temporal_env))
    assert response.status_code == 503
    assert response.json() == {
        "error": {"code": "unhealthy", "message": f"home: {home} has no AGENTS.md"}
    }


async def test_startup_creates_missing_case_store(home: Path, tmp_path: Path) -> None:
    cases_dir = tmp_path / "not-yet"
    app = create_app(make_settings(home, cases_dir, temporal_address=CLOSED_PORT))
    assert not cases_dir.exists()
    async with app.router.lifespan_context(app):
        assert cases_dir.is_dir()


async def test_cors_allows_only_the_web_origin(home: Path, cases_dir: Path) -> None:
    app = create_app(make_settings(home, cases_dir, temporal_address=CLOSED_PORT))
    preflight = {"Access-Control-Request-Method": "GET"}
    async with _client(app) as client:
        allowed = await client.options(
            "/api/health", headers={"Origin": "http://localhost:4710", **preflight}
        )
        denied = await client.options(
            "/api/health", headers={"Origin": "http://evil.test", **preflight}
        )
    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:4710"
    assert "access-control-allow-origin" not in denied.headers
