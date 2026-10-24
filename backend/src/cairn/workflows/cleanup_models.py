"""Inputs and outputs of `MemoryCleanupWorkflow` (design §7). Every tunable arrives in
`CleanupInput`, filled by `schedule ensure` from settings; the workflow never reads env."""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal

from pydantic import Field

from cairn.core.consolidate import ProposedChange
from cairn.core.lint import Finding, LintConfig
from cairn.core.model import Model

MAX_CLUSTERS = 5
SCHEDULE_ID = "memory-cleanup-weekly"
WORKFLOW_ID = "cleanup"  # the schedule appends the start time


class CleanupInput(Model):
    review_timeout: timedelta = timedelta(days=6)
    stale_days: int = 90
    dup_threshold: float = 0.82
    dup_body_threshold: float = 0.70
    memory_index_budget: int = 1500
    auto_apply_mechanical: bool = True
    tz: str = "Pacific/Auckland"

    def lint_config(self, skill_mounts: tuple[Path, ...]) -> LintConfig:
        return LintConfig(
            memory_index_budget=self.memory_index_budget,
            stale_days=self.stale_days,
            dup_threshold=self.dup_threshold,
            dup_body_threshold=self.dup_body_threshold,
            skill_mounts=skill_mounts,
        )


CleanupStatus = Literal[
    "linting",
    "drafting",
    "awaiting_review",
    "applying",
    "applied",
    "rejected",
    "expired",
    "no_changes",
    "failed",
]


class Proposal(Model):
    findings: list[Finding] = Field(default_factory=list[Finding])
    changes: list[ProposedChange] = Field(default_factory=list[ProposedChange])
    mechanical: list[str] = Field(default_factory=list[str])  # change ids applied without review


class ReviewDecision(Model):
    approved_op_ids: list[str]
    reviewer: str = ""
    reviewer_note: str = ""


class RejectedChange(Model):
    op_id: str
    reason: str


class CleanupOutcome(Model):
    applied: list[str] = Field(default_factory=list[str])  # op ids
    rejected: list[RejectedChange] = Field(default_factory=list[RejectedChange])


class CleanupState(Model):
    """The `get_state` query result and the API's cleanup view."""

    workflow_id: str
    status: CleanupStatus = "linting"
    started: datetime | None = None
    expires: datetime | None = None
    error: str | None = None
    proposal: Proposal | None = None
    decision: ReviewDecision | None = None
    outcome: CleanupOutcome | None = None


# --- activity payloads ----------------------------------------------------------------------


class LintIn(Model):
    workflow_id: str
    now: datetime
    config: CleanupInput


class Cluster(Model):
    slugs: list[str]
    base_hashes: dict[str, str]


class LintOut(Model):
    findings: list[Finding]
    archives: list[ProposedChange]
    clusters: list[Cluster]
    index_drift: bool


class MechanicalIn(Model):
    workflow_id: str
    now: datetime


class DraftIn(Model):
    workflow_id: str
    cluster: Cluster
    now: datetime
    tz: str


class DraftOut(Model):
    change: ProposedChange | None = None
    finding: Finding | None = None  # "could not draft a faithful merge"


class ApplyChangesIn(Model):
    workflow_id: str
    changes: list[ProposedChange]
    now: datetime
