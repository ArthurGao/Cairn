"""Memory cleanup (design §7, §11): proposals, the person's review, a manual trigger."""

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from temporalio.client import Client, WorkflowExecutionStatus
from temporalio.service import RPCError, RPCStatusCode

from cairn.api.schemas import Accepted, CleanupBrief, ErrorResponse
from cairn.api.services import Services, services
from cairn.api.workflows import workflow_view
from cairn.errors import CairnError, Conflict, Invalid, NotFound
from cairn.schedule import trigger_cleanup
from cairn.workflows.cleanup_models import WORKFLOW_ID, CleanupState, ReviewDecision
from cairn.workflows.memory_cleanup import MemoryCleanupWorkflow

router = APIRouter(prefix="/api/cleanup", tags=["cleanup"])
Deps = Annotated[Services, Depends(services)]
ERRORS: dict[int | str, dict[str, Any]] = {
    code: {"model": ErrorResponse} for code in (404, 409, 422, 503)
}


async def _state(client: Client, workflow_id: str) -> CleanupState:
    missing = NotFound(f"no cleanup {workflow_id}", code="cleanup_not_found")
    if not workflow_id.startswith(WORKFLOW_ID):
        raise missing

    def stopped(status: str | None) -> CleanupState:
        if status is None:
            return CleanupState(workflow_id=workflow_id)
        return CleanupState(
            workflow_id=workflow_id, status="failed", error=f"the cleanup stopped ({status})"
        )

    handle = client.get_workflow_handle_for(MemoryCleanupWorkflow.run, workflow_id)
    return await workflow_view(handle, MemoryCleanupWorkflow.get_state, missing, stopped)


@router.get("", response_model=list[CleanupBrief], responses=ERRORS, operation_id="listCleanups")
async def list_cleanups(
    deps: Deps, limit: Annotated[int, Query(ge=1, le=50)] = 10
) -> list[CleanupBrief]:
    client = await deps.temporal.client()
    briefs: list[CleanupBrief] = []
    async for execution in client.list_workflows(
        'WorkflowType="MemoryCleanupWorkflow"', limit=limit
    ):
        # From the memo the workflow keeps current: no query (needs a worker) or result per row.
        memo = await execution.memo()
        closed_early = execution.status not in (
            WorkflowExecutionStatus.RUNNING,
            WorkflowExecutionStatus.COMPLETED,
        )
        expires = memo.get("expires")
        briefs.append(
            CleanupBrief(
                workflow_id=execution.id,
                status="failed" if closed_early else memo.get("status", "linting"),
                started=execution.start_time,
                expires=datetime.fromisoformat(expires) if expires else None,
                changes=int(memo.get("changes", 0)),
            )
        )
    return briefs


@router.post(
    "/run", status_code=202, response_model=Accepted, responses=ERRORS, operation_id="runCleanup"
)
async def run_cleanup(deps: Deps) -> Accepted:
    client = await deps.temporal.client()
    try:
        await trigger_cleanup(client)
    except RPCError as exc:
        if exc.status != RPCStatusCode.NOT_FOUND:
            raise
        raise CairnError(
            "the cleanup schedule does not exist yet; start the worker or run "
            "`cairn schedule ensure`",
            code="schedule_missing",
            status=503,
        ) from exc
    return Accepted()


@router.get(
    "/{workflow_id}", response_model=CleanupState, responses=ERRORS, operation_id="getCleanup"
)
async def get_cleanup(workflow_id: str, deps: Deps) -> CleanupState:
    return await _state(await deps.temporal.client(), workflow_id)


@router.post(
    "/{workflow_id}/review",
    status_code=202,
    response_model=Accepted,
    responses=ERRORS,
    operation_id="reviewCleanup",
)
async def review_cleanup(workflow_id: str, decision: ReviewDecision, deps: Deps) -> Accepted:
    client = await deps.temporal.client()
    state = await _state(client, workflow_id)
    if state.status != "awaiting_review" or state.proposal is None:
        raise Conflict(
            f"cleanup {workflow_id} is {state.status}, not awaiting review",
            code="not_awaiting_review",
        )
    known = {c.op_id for c in state.proposal.changes}
    if unknown := [op for op in decision.approved_op_ids if op not in known]:
        raise Invalid(f"not in the proposal: {', '.join(unknown)}", code="unknown_op")
    handle = client.get_workflow_handle_for(MemoryCleanupWorkflow.run, workflow_id)
    await handle.signal(MemoryCleanupWorkflow.submit_review, decision)
    return Accepted()
