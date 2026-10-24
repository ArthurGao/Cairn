"""The weekly cleanup schedule (design §7.1). `ensure` is idempotent: the worker calls it at
startup and `cairn schedule ensure` runs it by hand; both write the current settings into the
schedule's workflow input, since workflows never read settings."""

from datetime import timedelta
from typing import Literal

from temporalio.client import (
    Client,
    Schedule,
    ScheduleActionExecutionStartWorkflow,
    ScheduleActionStartWorkflow,
    ScheduleAlreadyRunningError,
    ScheduleOverlapPolicy,
    SchedulePolicy,
    ScheduleSpec,
    ScheduleUpdate,
    ScheduleUpdateInput,
)

from cairn.errors import Conflict
from cairn.settings import Settings
from cairn.workflows.cleanup_models import SCHEDULE_ID, WORKFLOW_ID, CleanupInput
from cairn.workflows.memory_cleanup import MemoryCleanupWorkflow

CATCHUP_WINDOW = timedelta(days=1)


def cleanup_input(settings: Settings) -> CleanupInput:
    return CleanupInput(
        review_timeout=settings.review_timeout,
        stale_days=settings.stale_days,
        dup_threshold=settings.dup_threshold,
        dup_body_threshold=settings.dup_body_threshold,
        memory_index_budget=settings.memory_index_budget,
        auto_apply_mechanical=settings.auto_apply_mechanical,
        tz=settings.tz,
    )


def cleanup_schedule(settings: Settings) -> Schedule:
    return Schedule(
        action=ScheduleActionStartWorkflow(
            MemoryCleanupWorkflow.run,
            cleanup_input(settings),
            id=WORKFLOW_ID,
            task_queue=settings.task_queue,
        ),
        spec=ScheduleSpec(cron_expressions=[settings.cleanup_cron], time_zone_name=settings.tz),
        # SKIP: a cleanup still waiting for review blocks the next one (single flight).
        policy=SchedulePolicy(overlap=ScheduleOverlapPolicy.SKIP, catchup_window=CATCHUP_WINDOW),
    )


async def ensure_schedule(client: Client, settings: Settings) -> Literal["created", "updated"]:
    schedule = cleanup_schedule(settings)
    try:
        await client.create_schedule(SCHEDULE_ID, schedule)
        return "created"
    except ScheduleAlreadyRunningError:

        def update(_: ScheduleUpdateInput) -> ScheduleUpdate:
            return ScheduleUpdate(schedule=schedule)

        await client.get_schedule_handle(SCHEDULE_ID).update(update)
        return "updated"


async def trigger_cleanup(client: Client) -> None:
    """Start a cleanup now; refuse while one runs (a SKIP trigger would be silently dropped)."""
    handle = client.get_schedule_handle(SCHEDULE_ID)
    description = await handle.describe()
    if running := description.info.running_actions:
        ids = [
            a.workflow_id for a in running if isinstance(a, ScheduleActionExecutionStartWorkflow)
        ]
        raise Conflict(f"a cleanup is still running: {', '.join(ids)}", code="cleanup_in_progress")
    await handle.trigger()
