"""Activities of `AgentRunWorkflow` (design §6). Files, models and the writer live here.

Tools are read-only (D-05). Write-back goes through `core.validate` and `core.writer`, and the
run record and usage update are idempotent per run, so a retried activity changes nothing twice.
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from temporalio import activity

from cairn.activities.common import call_llm, parse_reply, permanent
from cairn.core.context import build_context
from cairn.core.index import find_skill, read_index, read_memory_text, read_skill_file
from cairn.core.runs import RunRecord, RunTokens, write_run_record
from cairn.core.tokens import estimate_tokens
from cairn.core.usage import load_usage, record_run, save_usage
from cairn.core.validate import conflict_rejections, plan_writeback
from cairn.core.writer import apply, home_lock, text_hash
from cairn.errors import CairnError
from cairn.llm.client import LlmClient
from cairn.llm.prompts import load_prompt
from cairn.llm.roles import Role
from cairn.llm.types import LlmRequest, LlmResult, Message, ToolSpec, ToolUsePart
from cairn.settings import Settings
from cairn.workflows.run_models import (
    L1_CHARS,
    L2_CHARS,
    AppliedOp,
    ApplyIn,
    ContextOut,
    ExtractIn,
    ExtractOut,
    LlmStepIn,
    RecordIn,
    RunInput,
    ToolOut,
    WritebackProposal,
    WritebackResult,
)

TOOLS = [
    ToolSpec(
        name="read_memory",
        description="Read one memory by its slug (from the memory index).",
        parameters={
            "type": "object",
            "properties": {"slug": {"type": "string"}},
            "required": ["slug"],
            "additionalProperties": False,
        },
    ),
    ToolSpec(
        name="load_skill",
        description="Load a skill's instructions by name (from the skill index).",
        parameters={
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
            "additionalProperties": False,
        },
    ),
    ToolSpec(
        name="read_skill_file",
        description="Read a reference file of a skill, by the relative path its body gives.",
        parameters={
            "type": "object",
            "properties": {"name": {"type": "string"}, "path": {"type": "string"}},
            "required": ["name", "path"],
            "additionalProperties": False,
        },
    ),
]


def _loaded(text: str, limit: int, **extra: Any) -> ToolOut:
    """Cut `text` to the level's budget (§5) and count what the model will see."""
    content, cut = text, False
    if len(text) > limit:
        content, cut = (
            text[:limit] + f"\n[cut: {len(text) - limit} more characters not shown]",
            True,
        )
    return ToolOut(
        content=content,
        chars=len(text),
        tokens=estimate_tokens(content),
        truncated=cut,
        **extra,
    )


class AgentActivities:
    def __init__(self, settings: Settings, client: LlmClient):
        self.settings = settings
        self.client = client

    @property
    def home(self) -> Path:
        return self.settings.home

    @activity.defn
    @permanent
    async def build_run_context(self, run: RunInput) -> ContextOut:
        context = build_context(
            self.home, run.l0_budget, run.memory_index_budget, self.settings.skill_mounts
        )
        _, template = load_prompt("agent_main")
        return ContextOut(
            system=template.format(context=context.prompt), breakdown=context.breakdown
        )

    @activity.defn
    @permanent
    async def agent_step(self, step: LlmStepIn) -> LlmResult:
        version, _ = load_prompt("agent_main")
        return await call_llm(
            self.client,
            LlmRequest(
                role=Role.AGENT_MAIN,
                system=step.system,
                cache_system=True,  # the same L0 and tools open every step of the run
                messages=step.messages,
                tools=TOOLS,
                prompt_version=version,
            ),
        )

    @activity.defn
    @permanent
    async def run_tool(self, call: ToolUsePart) -> ToolOut:
        """Read-only tools; an unknown name or a bad argument is an error result, not a crash."""
        try:
            return self._tool(call)
        except (CairnError, OSError, KeyError) as exc:
            message = exc.message if isinstance(exc, CairnError) else str(exc)
            return ToolOut(
                content=f"error: {message}", chars=0, tokens=0, truncated=False, error=True
            )

    def _tool(self, call: ToolUsePart) -> ToolOut:
        args = call.args
        if call.name == "read_memory":
            slug = str(args["slug"])
            text = read_memory_text(self.home, slug)
            return _loaded(
                text, L1_CHARS, loaded=f"memory:{slug}", slug=slug, read_hash=text_hash(text)
            )
        skill = find_skill(self.home, self.settings.skill_mounts, str(args["name"]))
        if call.name == "load_skill":
            return _loaded(skill.file.body, L1_CHARS, loaded=f"skill:{skill.name}")
        if call.name == "read_skill_file":
            relative, text = read_skill_file(skill, str(args["path"]))
            return _loaded(text, L2_CHARS, loaded=f"skillfile:{skill.name}/{relative}")
        raise CairnError(f"unknown tool {call.name}", code="unknown_tool")

    @activity.defn
    @permanent
    async def extract_writeback(self, job: ExtractIn) -> ExtractOut:
        version, template = load_prompt("memory_extract")
        transcript = "\n\n".join(job.transcript) or "(no tools were used)"
        request = LlmRequest(
            role=Role.MEMORY_EXTRACT,
            system=template.format(index=read_index(self.home) or "(empty)"),
            messages=[
                Message.user(
                    f"Task:\n{job.task}\n\nFinal answer:\n{job.answer}\n\n"
                    f"Tool results:\n{transcript}"
                )
            ],
            output_schema=WritebackProposal.model_json_schema(),
            prompt_version=version,
        )
        result = await call_llm(self.client, request)
        return ExtractOut(
            proposal=parse_reply(WritebackProposal, result),
            tokens_in=result.tokens_in,
            tokens_out=result.tokens_out,
        )

    @activity.defn
    @permanent
    async def apply_writeback(self, job: ApplyIn) -> WritebackResult:
        today = job.now.astimezone(ZoneInfo(job.tz)).date()
        plan = plan_writeback(
            self.home, job.ops, job.sources, job.run_id, job.read_hashes, today, job.dup_threshold
        )
        result = apply(self.home, plan.groups, f"run:{job.run_id}", job.now)
        return WritebackResult(
            applied=[
                AppliedOp(change_id=e.id, op=e.op, slug=e.slug, before=e.before, after=e.after)
                for e in result.applied
            ],
            rejected=[*plan.rejected, *conflict_rejections(plan, result)],
        )

    @activity.defn
    @permanent
    async def record_agent_run(self, job: RecordIn) -> None:
        """Write the run record (§4.6) and update usage, once per run."""
        state = job.state
        breakdown = state.context
        writeback = state.writeback
        record = RunRecord(
            run_id=state.run_id,
            started=state.started or job.now,
            status=state.status,
            tokens=RunTokens(
                l0=breakdown.l0_total if breakdown else 0,
                loaded=state.loaded_tokens,
                baseline_all=breakdown.baseline_all if breakdown else 0,
                input_total=job.tokens_in,
                output_total=job.tokens_out,
            ),
            loaded=state.loaded,
            applied=len(writeback.applied) if writeback else 0,
            rejected=len(writeback.rejected) if writeback else 0,
            error=state.error,
            task=state.task,
            outcome=job.summary or state.answer or "",
            open_items=job.open_items,
        )
        day = job.now.astimezone(ZoneInfo(job.tz)).date()
        with home_lock(self.home):
            if not write_run_record(self.home, day, record):
                return  # a retried activity: the run is already recorded
            read = [x.removeprefix("memory:") for x in state.loaded if x.startswith("memory:")]
            written = [a.slug for a in writeback.applied] if writeback else []
            save_usage(self.home, record_run(load_usage(self.home), read, written, day))

    def all(self) -> list[Callable[..., Any]]:
        return [
            self.build_run_context,
            self.agent_step,
            self.run_tool,
            self.extract_writeback,
            self.apply_writeback,
            self.record_agent_run,
        ]
