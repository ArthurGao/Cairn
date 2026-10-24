"""Activities of `MemoryCleanupWorkflow` (design §7): file reads, the model call and writes.

What to propose and how it applies is decided in `core.lint` and `core.consolidate`; writes go
through `core.writer`, idempotent by op id, so a retried activity changes nothing twice.
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from temporalio import activity

from cairn.activities.common import call_llm, parse_reply, permanent
from cairn.core.consolidate import (
    MergeDraft,
    archive_change,
    change_group,
    check_draft,
    merge_change,
    not_drafted,
)
from cairn.core.index import load_memories
from cairn.core.lint import lint_home
from cairn.core.usage import load_usage
from cairn.core.writer import apply, sync_index
from cairn.llm.client import LlmClient
from cairn.llm.prompts import load_prompt
from cairn.llm.roles import Role
from cairn.llm.types import LlmRequest, Message
from cairn.settings import Settings
from cairn.workflows.cleanup_models import (
    ApplyChangesIn,
    CleanupOutcome,
    Cluster,
    DraftIn,
    DraftOut,
    LintIn,
    LintOut,
    MechanicalIn,
    RejectedChange,
)


class CleanupActivities:
    def __init__(self, settings: Settings, client: LlmClient):
        self.settings = settings
        self.client = client

    @property
    def home(self) -> Path:
        return self.settings.home

    @activity.defn
    @permanent
    async def lint_for_cleanup(self, job: LintIn) -> LintOut:
        today = job.now.astimezone(ZoneInfo(job.config.tz)).date()
        config = job.config.lint_config(self.settings.skill_mounts)
        findings = lint_home(self.home, load_usage(self.home), today, config)
        texts = {m.slug: m.text for m in load_memories(self.home)[0]}
        return LintOut(
            findings=findings,
            archives=[
                archive_change(slug, texts.get(slug), f.base_hashes[slug], f.message)
                for f in findings
                if f.proposed == "archive"
                for slug in f.slugs
            ],
            clusters=[
                Cluster(slugs=f.slugs, base_hashes=f.base_hashes)
                for f in findings
                if f.proposed == "merge"
            ],
            index_drift=any(f.proposed == "index_sync" for f in findings),
        )

    @activity.defn
    @permanent
    async def apply_mechanical(self, job: MechanicalIn) -> list[str]:
        """Re-derive MEMORY.md (the only op applied without review, §7.2)."""
        entry = sync_index(self.home, f"cleanup:{job.workflow_id}", job.now)
        return [entry.id] if entry else []

    @activity.defn
    @permanent
    async def draft_merge(self, job: DraftIn) -> DraftOut:
        members = [m for m in load_memories(self.home)[0] if m.slug in job.cluster.slugs]
        version, system = load_prompt("memory_consolidate")
        files = "\n\n".join(f"=== {m.slug}.md ===\n{m.text}" for m in members)
        result = await call_llm(
            self.client,
            LlmRequest(
                role=Role.MEMORY_CONSOLIDATE,
                system=system,
                messages=[Message.user(files)],
                output_schema=MergeDraft.model_json_schema(),
                prompt_version=version,
            ),
        )
        draft = parse_reply(MergeDraft, result)
        check = check_draft(members, draft, job.now.astimezone(ZoneInfo(job.tz)).date())
        if check.text is None:
            return DraftOut(finding=not_drafted(job.cluster.slugs, check.problem or "refused"))
        return DraftOut(
            change=merge_change(members, draft.target_slug, check.text, job.cluster.base_hashes)
        )

    @activity.defn
    @permanent
    async def apply_changes(self, job: ApplyChangesIn) -> CleanupOutcome:
        groups = [change_group(c, job.workflow_id) for c in job.changes]
        result = apply(self.home, groups, f"cleanup:{job.workflow_id}", job.now)
        rejected = dict(result.rejected)
        return CleanupOutcome(
            applied=[
                c.op_id
                for c, g in zip(job.changes, groups, strict=True)
                if g.group_id not in rejected
            ],
            rejected=[
                RejectedChange(op_id=c.op_id, reason=rejected[g.group_id])
                for c, g in zip(job.changes, groups, strict=True)
                if g.group_id in rejected
            ],
        )

    def all(self) -> list[Callable[..., Any]]:
        return [self.lint_for_cleanup, self.apply_mechanical, self.draft_merge, self.apply_changes]
