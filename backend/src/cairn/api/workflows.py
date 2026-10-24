"""Reading a workflow's state for the API: its query while running, its result once closed."""

from collections.abc import Callable
from typing import Any

from temporalio.client import WorkflowExecutionStatus, WorkflowHandle
from temporalio.service import RPCError

from cairn.errors import NotFound


async def workflow_view[S](
    handle: WorkflowHandle[Any, S],
    query: Callable[[Any], S | None],
    missing: NotFound,
    stopped: Callable[[str | None], S],
) -> S:
    """`stopped(reason)` stands in for a workflow that has no state to show: one not started
    yet (reason None) or one that ended without a result (terminated, timed out, ...)."""
    try:
        description = await handle.describe()
        if description.status == WorkflowExecutionStatus.RUNNING:
            return await handle.query(query) or stopped(None)
        if description.status == WorkflowExecutionStatus.COMPLETED:
            return await handle.result()
    except RPCError as exc:
        raise missing from exc
    status = description.status.name.lower() if description.status else "unknown"
    return stopped(status)
