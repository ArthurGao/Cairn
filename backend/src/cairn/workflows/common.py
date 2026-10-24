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
# Model calls hit vendor rate limits, which clear within a minute or two: more attempts, and a
# vendor's Retry-After (the activity's next_retry_delay) replaces the backoff interval.
MODEL_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=2),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(minutes=1),
    maximum_attempts=8,
)


MODEL_TIMEOUT = timedelta(minutes=5)


async def act(method: Callable[..., Awaitable[Any]], arg: Any) -> Any:
    """A file activity."""
    return await workflow.execute_activity_method(
        method, arg, start_to_close_timeout=FILE_TIMEOUT, retry_policy=RETRY
    )


async def act_model(method: Callable[..., Awaitable[Any]], arg: Any) -> Any:
    """An activity that calls a model: the long timeout and the rate-limit-aware retries."""
    return await workflow.execute_activity_method(
        method, arg, start_to_close_timeout=MODEL_TIMEOUT, retry_policy=MODEL_RETRY
    )


def reason_of(error: ActivityError) -> str:
    """The activity's own message, not Temporal's wrapper text."""
    cause = error.cause
    return cause.message if isinstance(cause, ApplicationError) else str(cause or error)
