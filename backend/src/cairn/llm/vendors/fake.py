"""Scripted replies for tests and the full e2e stack; no network (design §10.1, §14).

A scenario is a JSON list of `{role, match?, reply, repeat?}`, from one file or several. A call
takes the first unused entry for its role whose `match` occurs in the request text; `repeat:
true` entries are never used up. A call no entry expects fails loudly — the fake is never lenient.
"""

import json
import re
from pathlib import Path
from typing import Any, cast

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


_DOC_HEADER = re.compile(r"=== document (?P<id>\S+) \((?P<name>[^)]+)\)")
_PLACEHOLDER = re.compile(r"\{\{doc:(?P<name>[^}]+)\}\}")


def _resolve(value: Any, doc_ids: dict[str, str]) -> Any:
    """Replace `{{doc:<filename>}}` with the id the request's page headers give that file,
    as a real model reads ids from those headers (ids are assigned at upload)."""
    if isinstance(value, str):
        return _PLACEHOLDER.sub(lambda m: doc_ids.get(m["name"], m[0]), value)
    if isinstance(value, list):
        return [_resolve(v, doc_ids) for v in cast(list[Any], value)]
    if isinstance(value, dict):
        return {k: _resolve(v, doc_ids) for k, v in cast(dict[str, Any], value).items()}
    return value


class FakeVendor:
    name = "fake"

    def __init__(self, *scenarios: Path):
        """Several files are one scenario, in the order given (e.g. case checks + agent run)."""
        self.entries = [
            FakeEntry.model_validate(e)
            for scenario in scenarios
            for e in json.loads(scenario.read_text(encoding="utf-8"))
        ]
        self.used: set[int] = set()
        self.calls: list[LlmRequest] = []

    async def complete(self, config: RoleConfig, request: LlmRequest) -> LlmResult:
        self.calls.append(request)
        haystack = request.system + "\n" + "\n".join(m.text() for m in request.messages)
        doc_ids = {m["name"]: m["id"] for m in _DOC_HEADER.finditer(haystack)}
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
                data=_resolve(reply.data, doc_ids) if reply.data is not None else None,
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
