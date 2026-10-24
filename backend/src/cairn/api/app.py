"""FastAPI app (design §11).

Run: `uv run uvicorn cairn.api.app:create_app --factory --port 4700`.
"""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException
from temporalio.client import Client

from cairn import temporal
from cairn.api.schemas import ErrorBody, ErrorResponse, HealthOk
from cairn.core.home import case_store_problem, home_problem
from cairn.errors import CairnError
from cairn.settings import Settings

TEMPORAL_TIMEOUT_S = 2.0

log = logging.getLogger(__name__)


class TemporalState:
    """A lazily connected client, dropped when a health probe finds it broken."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.client: Client | None = None

    async def probe(self) -> str | None:
        """Return None when Temporal answers, else the reason it did not."""
        try:
            async with asyncio.timeout(TEMPORAL_TIMEOUT_S):
                if self.client is None:
                    self.client = await temporal.connect(self.settings)
                await self.client.service_client.check_health()
        except Exception as exc:
            self.client = None
            reason = str(exc) or type(exc).__name__
            return f"unreachable at {self.settings.temporal_address} ({reason})"
        return None


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    state = TemporalState(settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        settings.cases_dir.mkdir(parents=True, exist_ok=True)
        yield

    app = FastAPI(title="Cairn API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.cors_origin],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    _install_error_handlers(app)

    @app.get(
        "/api/health",
        response_model=HealthOk,
        responses={503: {"model": ErrorResponse}},
        operation_id="getHealth",
    )
    async def health() -> HealthOk:
        problems: list[str] = []
        if reason := home_problem(settings.home):
            problems.append(f"home: {reason}")
        if reason := case_store_problem(settings.cases_dir):
            problems.append(f"cases: {reason}")
        if reason := await state.probe():
            problems.append(f"temporal: {reason}")
        if problems:
            raise CairnError("; ".join(problems), code="unhealthy", status=503)
        return HealthOk(
            status="ok",
            data_class=settings.data_class,
            temporal="ok",
            home=str(settings.home),
            cases=str(settings.cases_dir),
        )

    return app


def _error(status: int, code: str, message: str) -> JSONResponse:
    body = ErrorResponse(error=ErrorBody(code=code, message=message))
    return JSONResponse(status_code=status, content=body.model_dump())


def _install_error_handlers(app: FastAPI) -> None:
    """Every error leaves the API as `{error: {code, message}}` (design §11)."""

    @app.exception_handler(CairnError)
    async def _cairn(_: Request, exc: CairnError) -> JSONResponse:
        return _error(exc.status, exc.code, exc.message)

    @app.exception_handler(HTTPException)
    async def _http(_: Request, exc: HTTPException) -> JSONResponse:
        code = "not_found" if exc.status_code == 404 else f"http_{exc.status_code}"
        return _error(exc.status_code, code, str(exc.detail))

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        problems = "; ".join(
            f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()
        )
        return _error(422, "invalid_request", problems)

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled error", exc_info=exc)
        return _error(500, "internal", "Internal error; see the API log")
