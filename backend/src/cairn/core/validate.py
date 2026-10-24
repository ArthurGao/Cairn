"""Write-back validation (design §6.3): the model proposes memory ops; code decides.

Rules run in a fixed order and the first failure rejects the op with that rule's code; the
other ops still proceed. Accepted ops are rendered here (dates and source run set by code) and
returned as op groups for `core.writer.apply`, whose base-hash rejections become `conflict`.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from cairn.core.cases.citations import normalise_ws
from cairn.core.formats import MemoryFile, parse_memory, serialise, validate_memory
from cairn.core.index import load_memories, memory_path
from cairn.core.secrets import find_personal_data, find_secret
from cairn.core.similarity import similarity
from cairn.core.writer import ApplyResult, Op, OpGroup, text_hash
from cairn.errors import Invalid

RUN_LIMIT = 5
RuleCode = Literal[
    "run_limit",
    "schema",
    "evidence_missing",
    "secret",
    "personal_data",
    "duplicate",
    "not_found",
    "conflict",
]


class ProposedOp(BaseModel):
    """One op from `memory.extract`'s WritebackProposal."""

    op: Literal["create", "update"]
    slug: str
    type: str
    description: str
    body: str
    evidence: list[str] = Field(default_factory=list[str])
    reason: str = ""


class RejectedOp(BaseModel):
    index: int
    slug: str
    code: RuleCode
    reason: str


@dataclass(frozen=True)
class WritebackPlan:
    groups: list[OpGroup]  # one group per accepted op, group id = op id = "<run_id>:<index>"
    rejected: list[RejectedOp]
    slugs: dict[str, tuple[int, str]]  # group id -> (proposal index, slug)


class _Reject(Exception):
    def __init__(self, code: RuleCode, reason: str):
        super().__init__(reason)
        self.code: RuleCode = code
        self.reason = reason


def _render(proposal: ProposedOp, current: MemoryFile | None, run_id: str, today: date) -> str:
    """Code sets the dates and source run; an update keeps `created` and unknown keys."""
    if current is None:
        memory = MemoryFile(
            {
                "name": proposal.slug,
                "description": proposal.description,
                "metadata": {"type": proposal.type, "created": today},
            },
            "",
        )
    else:
        memory = MemoryFile(dict(current.front), "")
        memory.front["description"] = proposal.description
        memory.front["metadata"] = dict(current.meta())
    meta = memory.meta()
    meta["type"], meta["updated"], meta["source_run"] = proposal.type, today, run_id
    memory.front["metadata"] = meta
    memory.body = proposal.body.rstrip("\n") + "\n"
    return serialise(memory)


def _check(
    proposal: ProposedOp,
    current: MemoryFile | None,
    rendered: str,
    sources: str,
    others: Mapping[str, MemoryFile],
    dup_threshold: float,
) -> None:
    if errors := [
        i.message
        for i in validate_memory(parse_memory(rendered), proposal.slug)
        if i.severity == "error"
    ]:
        raise _Reject("schema", "; ".join(errors))
    evidence = [normalise_ws(e) for e in proposal.evidence if e.strip()]
    if not evidence:
        raise _Reject("evidence_missing", "no evidence given")
    if missing := [e for e in evidence if e not in sources]:
        raise _Reject("evidence_missing", f"not found in the run: {missing[0]!r}")
    text = proposal.description + "\n" + proposal.body
    if name := find_secret(text):
        raise _Reject("secret", f"matches the {name} pattern")
    if name := find_personal_data(text):
        raise _Reject("personal_data", f"matches the {name} pattern")
    if proposal.op == "create" and others:
        slug, score = max(
            ((s, similarity(proposal.description, m.description)) for s, m in others.items()),
            key=lambda pair: pair[1],
        )
        if score >= dup_threshold:
            raise _Reject("duplicate", f"description is {score:.2f} similar to {slug}")
    if proposal.op == "update" and current is None:
        raise _Reject("not_found", f"there is no memory {proposal.slug}")


def plan_writeback(
    home: Path,
    proposals: Sequence[ProposedOp],
    sources: Sequence[str],
    run_id: str,
    read_hashes: Mapping[str, str],
    today: date,
    dup_threshold: float,
) -> WritebackPlan:
    """Validate proposals against the run's text (`sources`: task, answer, tool results).

    `read_hashes` are the hashes `read_memory` returned during the run; an update of a memory
    the run did not read is based on the file as it is now.
    """
    haystack = normalise_ws("\n".join(sources))
    memories = {m.slug: m for m in load_memories(home)[0]}
    groups: list[OpGroup] = []
    rejected: list[RejectedOp] = []
    slugs: dict[str, tuple[int, str]] = {}
    for index, proposal in enumerate(proposals):
        try:
            if index >= RUN_LIMIT:
                raise _Reject("run_limit", f"only {RUN_LIMIT} ops per run are considered")
            try:
                path = memory_path(home, proposal.slug)
            except Invalid as exc:
                raise _Reject("schema", exc.message) from exc
            existing = memories.get(proposal.slug)
            current = existing.file if existing else None
            rendered = _render(proposal, current, run_id, today)
            others = {s: m.file for s, m in memories.items() if s != proposal.slug}
            _check(proposal, current, rendered, haystack, others, dup_threshold)
        except _Reject as reject:
            rejected.append(
                RejectedOp(index=index, slug=proposal.slug, code=reject.code, reason=reject.reason)
            )
            continue
        base = read_hashes.get(proposal.slug) or (
            text_hash(path.read_text(encoding="utf-8")) if existing else None
        )
        op_id = f"{run_id}:{index}"
        op = Op(
            op_id=op_id,
            op=proposal.op,
            slug=proposal.slug,
            after=rendered,
            base_hash=base,
            reason=proposal.reason,
        )
        groups.append(OpGroup(group_id=op_id, ops=[op]))
        slugs[op_id] = (index, proposal.slug)
    return WritebackPlan(groups, rejected, slugs)


def conflict_rejections(plan: WritebackPlan, result: ApplyResult) -> list[RejectedOp]:
    """The writer's rejected groups, as `conflict` rejections of the original proposals."""
    return [
        RejectedOp(
            index=plan.slugs[group_id][0],
            slug=plan.slugs[group_id][1],
            code="conflict",
            reason=reason,
        )
        for group_id, reason in result.rejected
    ]
