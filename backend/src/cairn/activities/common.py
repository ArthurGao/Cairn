"""Error mapping and model-call helpers shared by every activity module.

Vendor errors keep their retry class (design §10.3); domain errors and schema mismatches do not
heal on retry, so they fail the activity at once.
"""

import functools
from collections.abc import Awaitable, Callable
from datetime import timedelta

from pydantic import BaseModel, ValidationError
from temporalio.exceptions import ApplicationError

from cairn.errors import CairnError
from cairn.llm.client import LlmClient
from cairn.llm.types import LlmError, LlmRequest, LlmResult


def fatal(message: str, code: str) -> ApplicationError:
    return ApplicationError(message, type=code, non_retryable=True)


def permanent[**P, R](fn: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
    """Domain errors (missing case, page, spec...) do not heal on retry: fail at once."""

    @functools.wraps(fn)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return await fn(*args, **kwargs)
        except LlmError:
            raise
        except CairnError as exc:
            raise fatal(exc.message, exc.code) from exc

    return wrapper


async def call_llm(client: LlmClient, request: LlmRequest) -> LlmResult:
    """Retryable vendor errors go back to Temporal to retry, after the delay the vendor asked
    for when it gave one (a rate limit's Retry-After); the rest fail at once."""
    try:
        return await client.call(request)
    except LlmError as exc:
        if not exc.retryable:
            raise fatal(exc.message, exc.code) from exc
        delay = timedelta(seconds=exc.retry_after) if exc.retry_after is not None else None
        raise ApplicationError(exc.message, type=exc.code, next_retry_delay=delay) from exc


def parse_reply[T: BaseModel](model: type[T], result: LlmResult) -> T:
    try:
        return model.model_validate(result.data or {})
    except ValidationError as exc:
        raise fatal(f"{result.role}: reply does not match its schema: {exc}", "schema") from exc
