"""`CaseCheckWorkflow`: a consistency or pre-submission check over one case (design §8.1).

Fixed steps, so coverage is a property of code (D-13): every pending document is ingested,
every document is read for facts, every checklist item is sent to the model, and anything that
failed is reported as a gap or an `unable` item. Workflow code is deterministic: no I/O, no
clock (workflow.now()), no randomness; activities do the rest.
"""

import asyncio
from collections.abc import Awaitable, Callable, Sequence
from datetime import datetime, timedelta
from typing import Any

from pydantic import BaseModel
from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError, ApplicationError

with workflow.unsafe.imports_passed_through():
    from cairn.activities.cases import CaseActivities
    from cairn.core.cases.models import CallRecord, Dropped, Fact, ItemReply, ModelConflict
    from cairn.workflows.case_models import (
        CheckInput,
        CheckSpec,
        CheckState,
        CheckSummary,
        ExtractInput,
        FinishInput,
        IngestInput,
        ItemsInput,
        MarkFailedInput,
        MeasureInput,
        ProposeInput,
    )

FILE_TIMEOUT = timedelta(minutes=1)
MODEL_TIMEOUT = timedelta(minutes=10)
HEARTBEAT_TIMEOUT = timedelta(minutes=3)  # ingest/extract heartbeat per page or unit
RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=2), backoff_coefficient=2.0, maximum_attempts=3
)


def _reason(error: ActivityError) -> str:
    cause = error.cause
    return cause.message if isinstance(cause, ApplicationError) else str(cause or error)


async def _in_batches[T](jobs: Sequence[T], size: int, run: Callable[[T], Awaitable[None]]) -> None:
    """Bounded concurrency without wall-clock or threads: gather in fixed-size batches."""
    for start in range(0, len(jobs), max(1, size)):
        await asyncio.gather(*(run(job) for job in jobs[start : start + size]))


@workflow.defn
class CaseCheckWorkflow:
    def __init__(self) -> None:
        self._state: CheckState | None = None
        self._calls: list[CallRecord] = []

    @workflow.query
    def get_state(self) -> CheckState | None:
        return self._state

    async def _step[R](
        self, method: Callable[..., Awaitable[R]], job: BaseModel, *, model: bool = True
    ) -> R | str:
        """Run one activity; return its outcome, or the reason it failed after retries.

        Model steps heartbeat and get the long timeout; their call records are collected.
        """
        options: dict[str, Any] = {
            "start_to_close_timeout": MODEL_TIMEOUT if model else FILE_TIMEOUT,
            "retry_policy": RETRY,
        }
        if model:
            options["heartbeat_timeout"] = HEARTBEAT_TIMEOUT
        try:
            outcome = await workflow.execute_activity_method(method, job, **options)
        except ActivityError as error:
            return _reason(error)
        self._calls += getattr(outcome, "calls", [])
        return outcome

    @workflow.run
    async def run(self, check: CheckInput) -> CheckSummary:
        state = self._state = CheckState(
            check_id=check.check_id, case_id=check.case_id, kind=check.kind
        )
        started = workflow.now()
        spec = await self._step(CaseActivities.load_check_spec, check, model=False)
        if isinstance(spec, str):
            return await self._finish(state, check, started, error=spec)

        state.step = "ingesting"
        state.documents_total = len(spec.doc_ids)
        state.documents_done = len(spec.doc_ids) - len(spec.pending_doc_ids)

        async def ingest(doc_id: str) -> None:
            job = IngestInput(
                case_id=check.case_id,
                doc_id=doc_id,
                min_page_chars=check.min_page_chars,
                max_pages_per_case=check.max_pages_per_case,
            )
            outcome = await self._step(CaseActivities.ingest_document, job)
            if isinstance(outcome, str):
                mark = MarkFailedInput(case_id=check.case_id, doc_id=doc_id, error=outcome)
                # If even this fails, the document stays pending and is reported as a gap.
                await self._step(CaseActivities.mark_document_failed, mark, model=False)
            state.documents_done += 1

        await _in_batches(spec.pending_doc_ids, check.concurrency, ingest)
        if check.kind == "consistency":
            return await self._consistency(state, check, spec, started)
        return await self._presubmission(state, check, spec, started)

    async def _consistency(
        self, state: CheckState, check: CheckInput, spec: CheckSpec, started: datetime
    ) -> CheckSummary:
        state.step = "extracting"
        state.units_total = len(spec.doc_ids)
        per_doc: dict[str, list[Fact]] = {}
        dropped: list[Dropped] = []
        failures: dict[str, str] = {}

        async def extract(doc_id: str) -> None:
            job = ExtractInput(case_id=check.case_id, doc_id=doc_id, map_budget=check.map_budget)
            outcome = await self._step(CaseActivities.extract_facts, job)
            if isinstance(outcome, str):
                failures[doc_id] = f"fact extraction failed: {outcome}"
            else:
                per_doc[doc_id] = outcome.facts
                dropped.extend(outcome.dropped)
            state.units_done += 1

        await _in_batches(spec.doc_ids, check.concurrency, extract)
        # Ids in manifest order, so they do not depend on which activity finished first.
        facts: list[Fact] = []
        for doc_id in spec.doc_ids:
            for fact in per_doc.get(doc_id, []):
                facts.append(fact.model_copy(update={"fact_id": f"f{len(facts) + 1}"}))

        state.step = "comparing"
        proposals: list[ModelConflict] = []
        model_error: str | None = None
        if facts:
            job = ProposeInput(
                case_id=check.case_id, facts=facts, case_context_budget=check.case_context_budget
            )
            outcome = await self._step(CaseActivities.propose_conflicts, job)
            if isinstance(outcome, str):
                model_error = f"model comparison skipped, rule baseline only: {outcome}"
            else:
                proposals = outcome.proposals
        return await self._finish(
            state,
            check,
            started,
            facts=facts,
            dropped=dropped,
            proposals=proposals,
            model_error=model_error,
            extraction_failures=failures,
        )

    async def _presubmission(
        self, state: CheckState, check: CheckInput, spec: CheckSpec, started: datetime
    ) -> CheckSummary:
        skill = check.checklist_skill or ""
        measured = await self._step(
            CaseActivities.measure_case,
            MeasureInput(case_id=check.case_id, budget=check.case_context_budget),
            model=False,
        )
        if isinstance(measured, str):
            return await self._finish(state, check, started, error=measured)

        state.step = "checking"
        ids = [item.id for item in spec.items]
        size = max(1, check.item_batch_size)
        batches = [ids[i : i + size] for i in range(0, len(ids), size)]
        state.units_total = len(batches)
        replies: list[ItemReply] = []
        failed: list[str] = []

        async def run_batch(batch: list[str]) -> None:
            job = ItemsInput(case_id=check.case_id, checklist_skill=skill, item_ids=batch)
            outcome = await self._step(CaseActivities.check_items, job)
            if isinstance(outcome, str):
                failed.extend(batch)
            else:
                replies.extend(outcome.replies)
            state.units_done += 1

        await _in_batches(batches, check.concurrency, run_batch)
        return await self._finish(state, check, started, replies=replies, failed_items=failed)

    async def _finish(
        self, state: CheckState, check: CheckInput, started: datetime, **fields: object
    ) -> CheckSummary:
        state.step = "writing"
        job = FinishInput.model_validate(
            {
                "check": check,
                "started": started,
                "finished": workflow.now(),
                "calls": self._calls,
                **fields,
            }
        )
        try:
            summary: CheckSummary = await workflow.execute_activity_method(
                CaseActivities.write_result,
                job,
                start_to_close_timeout=FILE_TIMEOUT,
                retry_policy=RETRY,
            )
        except ActivityError as error:
            state.step, state.error = "failed", f"could not write the result: {_reason(error)}"
            raise
        state.step = "failed" if summary.status == "failed" else "done"
        state.error = summary.error
        return summary
