"""The always-loaded context (L0) and its token budget (design §5, §4.2).

`build_context` is what the agent sees up front: the home's AGENTS.md, the skill index and the
memory index. `baseline_all` is what loading every memory body and SKILL.md body eagerly would
cost; the gap between the two is the product's main claim.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel

from cairn.core.index import index_lines, load_memories, load_skills, skill_index_lines
from cairn.core.tokens import estimate_tokens
from cairn.errors import CairnError

SKILLS_HEADING = "## Skills (load one with load_skill before doing a task it covers)\n"
MEMORY_HEADING = "## Memory index (read a memory only when its description is relevant)\n"


class ContextBudgetError(CairnError):
    code = "context_budget"
    status = 422


class ContextBreakdown(BaseModel):
    agents_md: int
    skill_index: int
    memory_index: int
    l0_total: int
    baseline_all: int
    omitted_index_lines: int


@dataclass(frozen=True)
class Context:
    prompt: str
    breakdown: ContextBreakdown


def _section(heading: str, lines: Sequence[str]) -> str:
    return heading + "".join(f"{line}\n" for line in lines)


def build_context(
    home: Path,
    l0_budget: int,
    memory_index_budget: int,
    skill_mounts: Sequence[Path] = (),
) -> Context:
    agents_md = (home / "AGENTS.md").read_text(encoding="utf-8")
    memories, _ = load_memories(home)
    skills = load_skills(home, skill_mounts).skills

    skill_section = _section(SKILLS_HEADING, skill_index_lines(skills))
    fixed = estimate_tokens(agents_md) + estimate_tokens(skill_section)
    if fixed > l0_budget:
        raise ContextBudgetError(
            f"AGENTS.md and the skill index need {fixed} tokens; CAIRN_L0_BUDGET is {l0_budget}"
        )

    # The index is already ordered user, feedback, project, reference: trimming from the end
    # keeps user and feedback lines first (§4.2). Omitted lines are stated, never silent.
    allowance = min(memory_index_budget, l0_budget - fixed)
    lines = index_lines(memories)
    kept = len(lines)
    while kept and estimate_tokens(_memory_section(lines, kept)) > allowance:
        kept -= 1
    memory_section = _memory_section(lines, kept)

    prompt = f"{agents_md.rstrip()}\n\n{skill_section}\n{memory_section}"
    baseline = (
        estimate_tokens(agents_md)
        + sum(estimate_tokens(m.file.body) for m in memories)
        + sum(estimate_tokens(s.file.body) for s in skills)
    )
    breakdown = ContextBreakdown(
        agents_md=estimate_tokens(agents_md),
        skill_index=estimate_tokens(skill_section),
        memory_index=estimate_tokens(memory_section),
        l0_total=estimate_tokens(prompt),
        baseline_all=baseline,
        omitted_index_lines=len(lines) - kept,
    )
    return Context(prompt, breakdown)


def _memory_section(lines: Sequence[str], kept: int) -> str:
    shown = list(lines[:kept])
    if omitted := len(lines) - kept:
        shown.append(f"({omitted} more memories not shown: the index is over its token budget)")
    return _section(MEMORY_HEADING, shown)
