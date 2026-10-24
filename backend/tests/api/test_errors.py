"""Every error leaves the API in one shape: {error: {code, message}} (design §11)."""

from pathlib import Path

import httpx
from fastapi import FastAPI

from cairn.api.app import create_app
from tests.support import make_settings


def _app(home: Path, cases_dir: Path) -> FastAPI:
    app = create_app(make_settings(home, cases_dir, temporal_address="127.0.0.1:1"))

    @app.get("/api/test/needs-int")
    async def needs_int(n: int) -> int:  # pyright: ignore[reportUnusedFunction]
        return n

    @app.get("/api/test/boom")
    async def boom() -> None:  # pyright: ignore[reportUnusedFunction]
        raise RuntimeError("secret detail that must not leak")

    return app


async def _get(app: FastAPI, path: str) -> httpx.Response:
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(path)


async def test_unknown_route_is_not_found(home: Path, cases_dir: Path) -> None:
    response = await _get(_app(home, cases_dir), "/api/nope")
    assert response.status_code == 404
    assert response.json() == {"error": {"code": "not_found", "message": "Not Found"}}


async def test_invalid_query_is_invalid_request(home: Path, cases_dir: Path) -> None:
    response = await _get(_app(home, cases_dir), "/api/test/needs-int?n=abc")
    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "invalid_request",
            "message": (
                "query.n: Input should be a valid integer, unable to parse string as an integer"
            ),
        }
    }


async def test_unhandled_error_is_internal_without_detail(home: Path, cases_dir: Path) -> None:
    response = await _get(_app(home, cases_dir), "/api/test/boom")
    assert response.status_code == 500
    assert response.json() == {
        "error": {"code": "internal", "message": "Internal error; see the API log"}
    }
