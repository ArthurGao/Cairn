"""Activity-call defaults and error text shared by every workflow (deterministic: no I/O)."""

from collections.abc import Awaitable, Callable
from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError, ApplicationError

FILE_TIMEOUT = timedelta(minutes=1)
RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=2), backoff_coefficient=2.0, maximum_attempts=3
)


async def act(
    method: Callable[..., Awaitable[Any]], arg: Any, limit: timedelta = FILE_TIMEOUT
) -> Any:
    return await workflow.execute_activity_method(
        method, arg, start_to_close_timeout=limit, retry_policy=RETRY
    )


def reason_of(error: ActivityError) -> str:
    """The activity's own message, not Temporal's wrapper text."""
    cause = error.cause
    return cause.message if isinstance(cause, ApplicationError) else str(cause or error)
