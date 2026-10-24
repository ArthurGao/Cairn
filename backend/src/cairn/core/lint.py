"""Health checks over a harness home (design §7.2). Code decides; each finding may propose an op.

The same function backs `cairn lint` and the weekly cleanup workflow.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from itertools import combinations
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from cairn.core.cases.spec import SpecInvalid, list_checklists, load_categories
from cairn.core.formats import Severity
from cairn.core.index import (
    Broken,
    Memory,
    index_current,
    indexed_slugs,
    load_memories,
    load_skills,
    memory_issues,
    read_index,
)
from cairn.core.similarity import normalise, normalised_similarity
from cairn.core.tokens import estimate_tokens
from cairn.core.usage import UsageEntry
from cairn.core.writer import text_hash

CONSISTENCY_SKILL = "case-consistency-check"
_SEVERITY_ORDER: dict[Severity, int] = {"error": 0, "warn": 1, "info": 2}


class Finding(BaseModel):
    check: str
    severity: Severity
    slugs: list[str]
    message: str
    proposed: Literal["index_sync", "archive", "merge"] | None = None
    # Hash of each slug's file at lint time: the base hash a proposed op is applied against
    # (§7.4), so a file edited during the review wait is rejected as a conflict.
    base_hashes: dict[str, str] = Field(default_factory=dict[str, str])


@dataclass(frozen=True)
class LintConfig:
    memory_index_budget: int = 1500
    stale_days: int = 90
    dup_threshold: float = 0.82
    dup_body_threshold: float = 0.70
    skill_mounts: tuple[Path, ...] = ()


def lint_home(
    home: Path, usage: dict[str, UsageEntry], today: date, config: LintConfig
) -> list[Finding]:
    memories, broken = load_memories(home)
    findings = [
        Finding(check="frontmatter_invalid", severity="error", slugs=[b.path.stem], message=b.error)
        for b in broken
    ]
    for slug, issues in memory_issues(memories).items():
        findings += [
            Finding(check=i.code, severity=i.severity, slugs=[slug], message=i.message)
            for i in issues
        ]
    findings += _index_findings(home, memories, broken, config)
    findings += _skill_findings(home, config)
    findings += _stale(memories, usage, today, config)
    findings += _duplicates(memories, config)
    return sorted(findings, key=lambda f: (_SEVERITY_ORDER[f.severity], f.check, f.slugs))


def _hash(memory: Memory) -> str:
    digest = text_hash(memory.text)
    assert digest is not None
    return digest


def has_errors(findings: Sequence[Finding]) -> bool:
    return any(f.severity == "error" for f in findings)


def _index_findings(
    home: Path, memories: Sequence[Memory], broken: Sequence[Broken], config: LintConfig
) -> list[Finding]:
    current, rendered = index_current(home)
    indexed = set(indexed_slugs(read_index(home)))
    on_disk = {m.slug for m in memories}
    findings = [
        Finding(
            check=check,
            severity="warn",
            slugs=[slug],
            message=message.format(slug=slug),
            proposed="index_sync",
        )
        for check, slugs, message in (
            ("index_missing", on_disk - indexed, "{slug}.md is not in MEMORY.md"),
            ("index_orphan", indexed - on_disk, "MEMORY.md lists {slug}.md, which does not exist"),
        )
        for slug in sorted(slugs)
    ]
    if not findings and not current and not broken:
        findings.append(
            Finding(
                check="index_drift",
                severity="warn",
                slugs=[],
                message="MEMORY.md differs from the files (order, title or description)",
                proposed="index_sync",
            )
        )
    tokens = estimate_tokens(rendered)
    if tokens > config.memory_index_budget:
        findings.append(
            Finding(
                check="index_over_budget",
                severity="error",
                slugs=[],
                message=f"the memory index needs {tokens} tokens; the budget is "
                f"{config.memory_index_budget}",
            )
        )
    return findings


def _skill_findings(home: Path, config: LintConfig) -> list[Finding]:
    loaded = load_skills(home, config.skill_mounts)
    findings = [
        Finding(
            check=issue.code,
            severity=issue.severity,
            slugs=[path.parent.name],
            message=issue.message,
        )
        for path, issue in loaded.issues
    ]
    names = {s.name: s for s in loaded.skills}
    if CONSISTENCY_SKILL in names:
        try:
            load_categories(names[CONSISTENCY_SKILL].path)
        except (SpecInvalid, OSError) as exc:
            findings.append(
                Finding(
                    check="spec_invalid",
                    severity="error",
                    slugs=[CONSISTENCY_SKILL],
                    message=str(exc),
                )
            )
    findings += [
        Finding(check="spec_invalid", severity="error", slugs=[info.skill], message=info.error)
        for info in list_checklists(home / "skills")
        if info.error
    ]
    return findings


def _stale(
    memories: Sequence[Memory], usage: dict[str, UsageEntry], today: date, config: LintConfig
) -> list[Finding]:
    cutoff = today - timedelta(days=config.stale_days)
    findings: list[Finding] = []
    for memory in memories:
        if memory.file.type == "user":
            continue
        entry = usage.get(memory.slug, UsageEntry())
        if entry.reads >= 2:
            continue
        if entry.last_read is not None:
            stale, since = entry.last_read < cutoff, f"last read {entry.last_read}"
        else:
            created = memory.file.created()
            stale, since = (
                created is not None and created < cutoff,
                f"never read, created {created}",
            )
        if stale:
            findings.append(
                Finding(
                    check="stale",
                    severity="info",
                    slugs=[memory.slug],
                    message=f"{memory.slug}: {since}, {entry.reads} read(s)",
                    proposed="archive",
                    base_hashes={memory.slug: _hash(memory)},
                )
            )
    return findings


def _duplicates(memories: Sequence[Memory], config: LintConfig) -> list[Finding]:
    parent = {m.slug: m.slug for m in memories}

    def root(slug: str) -> str:
        while parent[slug] != slug:
            slug = parent[slug]
        return slug

    texts = {m.slug: (normalise(m.file.description), normalise(m.file.body)) for m in memories}
    scores: dict[frozenset[str], tuple[float, float]] = {}
    for a, b in combinations(memories, 2):
        desc = normalised_similarity(texts[a.slug][0], texts[b.slug][0])
        body = normalised_similarity(texts[a.slug][1], texts[b.slug][1])
        if desc >= config.dup_threshold or body >= config.dup_body_threshold:
            scores[frozenset((a.slug, b.slug))] = (desc, body)
            parent[root(a.slug)] = root(b.slug)

    clusters: dict[str, list[str]] = {}
    for memory in memories:
        clusters.setdefault(root(memory.slug), []).append(memory.slug)
    by_slug = {m.slug: m for m in memories}
    ordered = sorted(scores.items(), key=lambda kv: sorted(kv[0]))
    findings: list[Finding] = []
    for members in clusters.values():
        if len(members) < 2:
            continue
        pairs = [
            f"{'/'.join(sorted(pair))} description {d:.2f}, body {b:.2f}"
            for pair, (d, b) in ordered
            if pair <= set(members)
        ]
        findings.append(
            Finding(
                check="duplicate",
                severity="info",
                slugs=sorted(members),
                message="near-duplicates: " + "; ".join(pairs),
                proposed="merge",
                base_hashes={s: _hash(by_slug[s]) for s in sorted(members)},
            )
        )
    return findings
