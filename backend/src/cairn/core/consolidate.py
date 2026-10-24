"""Merge drafts for duplicate clusters (design §7.3): the model drafts, code accepts or refuses.

A draft is accepted only if its target is in the cluster, the merged file passes §4.1, nothing
secret or personal is in it, its evidence occurs in a source file, and every number, date, path,
URL and back-ticked identifier in the merged body occurs in at least one source file (fidelity).
"""

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from cairn.core.cases.citations import normalise_ws
from cairn.core.formats import MemoryFile, parse_memory, serialise, validate_memory
from cairn.core.index import Memory
from cairn.core.lint import Finding
from cairn.core.model import Model
from cairn.core.secrets import find_personal_data, find_secret
from cairn.core.writer import Op, OpGroup

# Facts a merge must not invent: back-ticked identifiers, URLs, paths, numbers and dates.
_FACTS = re.compile(
    r"`[^`\n]+`"
    r"|https?://[^\s)>\]]+"
    r"|(?<![\w/])(?:[\w.-]+/)+[\w.-]+"
    r"|(?<![\w-])[\w-]*\d[\w.,:/-]*"  # numbers, dates and words with a digit (v1, AEWV2)
)


class MergeDraft(BaseModel):
    """What `memory.consolidate` returns for one cluster; also its structured-output schema."""

    target_slug: str
    description: str
    body: str
    evidence: list[str] = Field(default_factory=list[str])


@dataclass(frozen=True)
class MergeCheck:
    text: str | None  # the merged target file, when accepted
    problem: str | None  # why the draft was refused


def facts(text: str) -> list[str]:
    return [m.rstrip(".,;:") for m in _FACTS.findall(text)]


def _occurs(fact: str, sources: str) -> bool:
    """As a whole token: `14` does not occur in `2026-07-14`, `MM/YYYY` does in `` `MM/YYYY` ``."""
    core = re.escape(fact.strip("`"))
    return re.search(rf"(?<![\w-]){core}(?![\w-])", sources) is not None


def _merged(target: MemoryFile, draft: MergeDraft, today: date) -> str:
    memory = MemoryFile(dict(target.front), draft.body.rstrip("\n") + "\n")
    memory.front["description"] = draft.description
    meta = dict(target.meta())
    meta["updated"] = today
    memory.front["metadata"] = meta
    return serialise(memory)


def check_draft(cluster: Sequence[Memory], draft: MergeDraft, today: date) -> MergeCheck:
    by_slug = {m.slug: m for m in cluster}
    if draft.target_slug not in by_slug:
        return MergeCheck(None, f"target {draft.target_slug!r} is not one of {sorted(by_slug)}")
    text = _merged(by_slug[draft.target_slug].file, draft, today)
    if errors := [
        i.message
        for i in validate_memory(parse_memory(text), draft.target_slug)
        if i.severity == "error"
    ]:
        return MergeCheck(None, "; ".join(errors))
    scanned = "\n".join((draft.description, draft.body))
    if name := find_secret(scanned):
        return MergeCheck(None, f"matches the {name} pattern")
    if name := find_personal_data(scanned):
        return MergeCheck(None, f"matches the {name} pattern")
    sources = "\n".join(m.text for m in cluster)
    flat = normalise_ws(sources)
    if missing := [e for e in draft.evidence if e.strip() and normalise_ws(e) not in flat]:
        return MergeCheck(None, f"evidence not in the cluster: {missing[0]!r}")
    if invented := [f for f in facts(draft.body) if not _occurs(f, sources)]:
        return MergeCheck(None, f"the merged body adds {invented[0]!r}, which no source has")
    return MergeCheck(text, None)


# --- proposed changes (§7.4): what a person approves, and the op group it applies as ---------


class FileChange(Model):
    slug: str
    before: str | None
    after: str | None  # None: moved to memory/_archive/


class ProposedChange(Model):
    """One checkbox in the review: an archive, or a whole merge (one op group, §7.3)."""

    op_id: str  # "archive:<slug>" | "merge:<target>"
    kind: Literal["archive", "merge"]
    reason: str
    changes: list[FileChange]  # a merge: the target first, then the members it archives
    base_hashes: dict[str, str]  # each file's hash at lint time (§7.4)


def archive_change(slug: str, text: str | None, base_hash: str, reason: str) -> ProposedChange:
    return ProposedChange(
        op_id=f"archive:{slug}",
        kind="archive",
        reason=f"stale: {reason}",
        changes=[FileChange(slug=slug, before=text, after=None)],
        base_hashes={slug: base_hash},
    )


def merge_change(
    cluster: Sequence[Memory], target: str, merged: str, base_hashes: Mapping[str, str]
) -> ProposedChange:
    by_slug = {m.slug: m for m in cluster}
    others = [m for m in cluster if m.slug != target]
    return ProposedChange(
        op_id=f"merge:{target}",
        kind="merge",
        reason=f"merge of {', '.join(m.slug for m in cluster)} into {target}",
        changes=[
            FileChange(slug=target, before=by_slug[target].text, after=merged),
            *(FileChange(slug=m.slug, before=m.text, after=None) for m in others),
        ],
        base_hashes={m.slug: base_hashes[m.slug] for m in cluster},
    )


def not_drafted(slugs: Sequence[str], why: str) -> Finding:
    """A merge that could not be drafted faithfully is a finding, never a weaker merge."""
    return Finding(
        check="merge_not_drafted",
        severity="info",
        slugs=list(slugs),
        message=f"could not draft a faithful merge: {why}",
    )


def change_group(change: ProposedChange, prefix: str) -> OpGroup:
    """All-or-nothing writer ops against the lint-time hashes; ids are stable per proposal."""
    group_id = f"{prefix}:{change.op_id}"
    return OpGroup(
        group_id=group_id,
        ops=[
            Op(
                op_id=f"{group_id}:{n}",
                op="archive" if file.after is None else "update",
                slug=file.slug,
                after=file.after,
                base_hash=change.base_hashes[file.slug],
                reason=change.reason,
            )
            for n, file in enumerate(change.changes)
        ],
    )
