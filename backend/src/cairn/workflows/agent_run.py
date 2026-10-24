"""`AgentRunWorkflow`: an agent run with progressive disclosure and validated write-back (§6).

The model works from the L0 context and loads detail through read-only tools; after the run,
`memory.extract` proposes memory ops once, code validates them, the writer applies them, and a
run record is written. Deterministic: no I/O, no clock but workflow.now(), no randomness.
"""

from collections.abc import Awaitable, Callable
from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError, ApplicationError

with workflow.unsafe.imports_passed_through():
    from cairn.activities.agent import AgentActivities
    from cairn.llm.types import LlmResult, Message, TextPart, ToolResultPart
    from cairn.workflows.run_models import (
        TRANSCRIPT_CHARS,
        ApplyIn,
        ExtractIn,
        LlmStepIn,
        RecordIn,
        RunInput,
        RunState,
        Step,
        WritebackResult,
    )

FILE_TIMEOUT = timedelta(minutes=1)
MODEL_TIMEOUT = timedelta(minutes=5)
RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=2), backoff_coefficient=2.0, maximum_attempts=3
)


def run_workflow_id(run_id: str) -> str:
    return f"run-{run_id}"


def _reason(error: ActivityError) -> str:
    cause = error.cause
    return cause.message if isinstance(cause, ApplicationError) else str(cause or error)


@workflow.defn
class AgentRunWorkflow:
    def __init__(self) -> None:
        self._state: RunState | None = None
        self._tokens_in = 0
        self._tokens_out = 0

    @workflow.query
    def get_state(self) -> RunState | None:
        return self._state

    async def _act(
        self, method: Callable[..., Awaitable[Any]], arg: Any, limit: timedelta = FILE_TIMEOUT
    ) -> Any:
        return await workflow.execute_activity_method(
            method, arg, start_to_close_timeout=limit, retry_policy=RETRY
        )

    @workflow.run
    async def run(self, run: RunInput) -> RunState:
        state = self._state = RunState(run_id=run.run_id, task=run.task, started=workflow.now())
        try:
            context = await self._act(AgentActivities.build_run_context, run)
        except ActivityError as error:
            return await self._end(run, state, error=_reason(error))
        state.context = context.breakdown

        messages = [Message.user(run.task)]
        transcript: list[str] = []
        read_hashes: dict[str, str] = {}  # what each memory looked like when the agent read it
        for _ in range(run.max_steps):
            try:
                reply: LlmResult = await self._act(
                    AgentActivities.agent_step,
                    LlmStepIn(system=context.system, messages=messages),
                    MODEL_TIMEOUT,
                )
            except ActivityError as error:
                return await self._end(run, state, error=_reason(error))
            self._tokens_in += reply.tokens_in
            self._tokens_out += reply.tokens_out
            state.steps.append(
                Step(
                    n=len(state.steps) + 1,
                    kind="llm",
                    role=reply.role,
                    tokens_in=reply.tokens_in,
                    tokens_out=reply.tokens_out,
                    model=reply.model,
                    at=workflow.now(),
                )
            )
            parts: list[Any] = [TextPart(text=reply.text)] if reply.text else []
            messages.append(Message(role="assistant", content=[*parts, *reply.tool_calls]))
            if not reply.tool_calls:
                state.answer = reply.text
                break
            results: list[Any] = []
            for call in reply.tool_calls:
                out = await self._act(AgentActivities.run_tool, call)
                arg = next(iter(call.args.values()), None) if call.args else None
                state.steps.append(
                    Step(
                        n=len(state.steps) + 1,
                        kind="tool",
                        tool=call.name,
                        arg=None if arg is None else str(arg),
                        result_chars=out.chars,
                        tokens=out.tokens,
                        truncated=out.truncated,
                        at=workflow.now(),
                    )
                )
                state.loaded_tokens += out.tokens
                if out.loaded and out.loaded not in state.loaded:
                    state.loaded.append(out.loaded)
                if out.slug and out.read_hash:
                    read_hashes.setdefault(out.slug, out.read_hash)
                transcript.append(f"[{call.name} {arg}]\n{out.content[:TRANSCRIPT_CHARS]}")
                results.append(ToolResultPart(tool_use_id=call.id, content=out.content))
            messages.append(Message(role="user", content=results))
        else:
            # Nothing trustworthy to extract from a run that never answered (§6.5).
            return await self._end(run, state, error="max_steps reached")

        state.status = "extracting"
        answer = state.answer or ""
        try:
            extracted = await self._act(
                AgentActivities.extract_writeback,
                ExtractIn(task=run.task, answer=answer, transcript=transcript),
                MODEL_TIMEOUT,
            )
        except ActivityError as error:
            # A failed extraction is never shown as "nothing to remember" (D-08).
            state.writeback = WritebackResult(error=f"memory extraction failed: {_reason(error)}")
            return await self._end(run, state)
        self._tokens_in += extracted.tokens_in
        self._tokens_out += extracted.tokens_out
        proposal = extracted.proposal

        state.status = "writing"
        try:
            state.writeback = await self._act(
                AgentActivities.apply_writeback,
                ApplyIn(
                    run_id=run.run_id,
                    ops=proposal.ops,
                    sources=[run.task, answer, *transcript],
                    read_hashes=read_hashes,
                    now=workflow.now(),
                    tz=run.tz,
                    dup_threshold=run.dup_threshold,
                ),
            )
        except ActivityError as error:
            state.writeback = WritebackResult(error=f"write-back failed: {_reason(error)}")
        return await self._end(run, state, summary=proposal.run_summary, items=proposal.open_items)

    async def _end(
        self,
        run: RunInput,
        state: RunState,
        error: str | None = None,
        summary: str = "",
        items: list[str] | None = None,
    ) -> RunState:
        state.status = "failed" if error else "completed"
        state.error = error
        await self._act(
            AgentActivities.record_agent_run,
            RecordIn(
                state=state,
                summary=summary,
                open_items=items or [],
                tokens_in=self._tokens_in,
                tokens_out=self._tokens_out,
                now=workflow.now(),
                tz=run.tz,
            ),
        )
        return state
