"""Scripted replies for tests and the full e2e stack; no network (design §10.1, §14).

A scenario is a JSON list of `{role, match?, reply, repeat?}`. A call takes the first unused
entry for its role whose `match` occurs in the request text; `repeat: true` entries are never
used up. A call no entry expects fails loudly — the fake is never lenient.
"""

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from cairn.llm.roles import RoleConfig
from cairn.llm.types import LlmError, LlmRequest, LlmResult, StopReason, ToolUsePart


class FakeReply(BaseModel):
    text: str = ""
    data: dict[str, Any] | None = None
    tool_calls: list[ToolUsePart] = Field(default_factory=list[ToolUsePart])
    stop_reason: StopReason = "end"
    tokens_in: int = 0
    tokens_out: int = 0
    error: str | None = None  # raise instead of replying
    retryable: bool = False


class FakeEntry(BaseModel):
    role: str
    match: str = ""
    reply: FakeReply
    repeat: bool = False


class FakeVendor:
    name = "fake"

    def __init__(self, scenario: Path):
        self.entries = [
            FakeEntry.model_validate(e) for e in json.loads(scenario.read_text(encoding="utf-8"))
        ]
        self.used: set[int] = set()
        self.calls: list[LlmRequest] = []

    async def complete(self, config: RoleConfig, request: LlmRequest) -> LlmResult:
        self.calls.append(request)
        haystack = request.system + "\n" + "\n".join(m.text() for m in request.messages)
        for n, entry in enumerate(self.entries):
            if n in self.used or entry.role != request.role.value or entry.match not in haystack:
                continue
            if not entry.repeat:
                self.used.add(n)
            reply = entry.reply
            if reply.error:
                raise LlmError(reply.error, retryable=reply.retryable, code="fake_error")
            return LlmResult(
                role=request.role,
                vendor=self.name,
                model=config.model,
                text=reply.text,
                data=reply.data,
                tool_calls=reply.tool_calls,
                stop_reason=reply.stop_reason,
                tokens_in=reply.tokens_in,
                tokens_out=reply.tokens_out,
            )
        first_line = haystack.strip().splitlines()[0][:120] if haystack.strip() else ""
        raise LlmError(
            f"fake vendor: no scenario entry for role {request.role.value} matching {first_line!r}",
            retryable=False,
            code="fake_unexpected_call",
        )
