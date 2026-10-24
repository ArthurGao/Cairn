"""Inputs and outputs of `AgentRunWorkflow` (design §6). Tool results are truncated before
they enter workflow history (§5 budgets)."""

from datetime import datetime
from typing import Literal

from pydantic import Field

from cairn.core.context import ContextBreakdown
from cairn.core.model import Model
from cairn.core.validate import ProposedOp, RejectedOp
from cairn.llm.types import Message

L1_CHARS = 8_000  # memory body, SKILL.md body
L2_CHARS = 20_000  # a skill reference file
TRANSCRIPT_CHARS = 2_000  # per tool result, as sent to memory.extract (§6.3)


class RunInput(Model):
    run_id: str
    task: str
    max_steps: int = 8
    l0_budget: int = 4000
    memory_index_budget: int = 1500
    dup_threshold: float = 0.82
    tz: str = "Pacific/Auckland"


RunStatus = Literal["running", "extracting", "writing", "completed", "failed"]


class Step(Model):
    n: int
    kind: Literal["llm", "tool"]
    role: str | None = None
    tool: str | None = None
    arg: str | None = None
    result_chars: int | None = None
    truncated: bool | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    tokens: int | None = None  # tool steps: estimated tokens of what was loaded
    model: str | None = None
    at: datetime


class AppliedOp(Model):
    change_id: str
    op: str
    slug: str
    before: str | None = None
    after: str | None = None
    undone: bool = False  # filled from the change log when the API serves the run


class WritebackResult(Model):
    applied: list[AppliedOp] = Field(default_factory=list[AppliedOp])
    rejected: list[RejectedOp] = Field(default_factory=list[RejectedOp])
    error: str | None = None


class RunState(Model):
    """The `get_state` query result and the API's run view (design §6.2)."""

    run_id: str
    task: str
    status: RunStatus = "running"
    error: str | None = None
    started: datetime | None = None
    context: ContextBreakdown | None = None
    steps: list[Step] = Field(default_factory=list[Step])
    loaded: list[str] = Field(default_factory=list[str])
    loaded_tokens: int = 0  # estimated; what tools loaded on top of L0
    answer: str | None = None
    writeback: WritebackResult | None = None


class ContextOut(Model):
    system: str
    breakdown: ContextBreakdown


class LlmStepIn(Model):
    system: str
    messages: list[Message]


class ToolOut(Model):
    content: str
    chars: int
    tokens: int  # estimated, of `content` as the model sees it
    truncated: bool
    loaded: str | None = None  # "memory:<slug>" | "skill:<name>" | "skillfile:<name>/<path>"
    slug: str | None = None
    read_hash: str | None = None
    error: bool = False


class ExtractIn(Model):
    task: str
    answer: str
    transcript: list[str]


class WritebackProposal(Model):
    """What `memory.extract` drafts (design §6.3); also its structured-output schema."""

    ops: list[ProposedOp] = Field(default_factory=list[ProposedOp])
    run_summary: str = Field(default="", max_length=800)
    open_items: list[str] = Field(default_factory=list[str])


class ExtractOut(Model):
    proposal: WritebackProposal
    tokens_in: int = 0
    tokens_out: int = 0


class ApplyIn(Model):
    run_id: str
    ops: list[ProposedOp]
    sources: list[str]
    read_hashes: dict[str, str]
    now: datetime
    tz: str
    dup_threshold: float


class RecordIn(Model):
    state: RunState
    summary: str = ""
    open_items: list[str] = Field(default_factory=list[str])
    tokens_in: int = 0
    tokens_out: int = 0
    now: datetime
    tz: str
