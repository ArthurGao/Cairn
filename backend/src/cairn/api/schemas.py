"""API models; the OpenAPI source for the frontend's generated client."""

from datetime import date, datetime
from typing import Literal

from pydantic import Field

from cairn.core.cases.models import (
    CheckKind,
    CheckResult,
    DataClass,
    Manifest,
    ReviewAction,
)
from cairn.core.context import ContextBreakdown
from cairn.core.model import Model
from cairn.core.usage import UsageEntry
from cairn.core.writer import ChangeEntry
from cairn.workflows.case_models import CheckState, SpecItem
from cairn.workflows.cleanup_models import CleanupStatus
from cairn.workflows.run_models import RunStatus


class ErrorBody(Model):
    code: str
    message: str


class ErrorResponse(Model):
    error: ErrorBody


class HealthOk(Model):
    status: Literal["ok"]
    data_class: Literal["synthetic", "client"]
    temporal: Literal["ok"]
    home: str
    cases: str


# --- cases (design §11) -----------------------------------------------------------------------


class CaseCreate(Model):
    label: str = Field(min_length=1, max_length=200)


class CaseCreated(Model):
    case_id: str


class SignOff(Model):
    adviser: str
    at: datetime


class CheckCounts(Model):
    conflicts: int = 0
    checked: int = 0
    pending: int = 0
    unable: int = 0
    concerns: int = 0
    not_supported: int = 0  # letter concerns the case's documents do not fully support
    gaps: int = 0
    clean: bool = False


class CheckBrief(Model):
    check_id: str
    kind: CheckKind
    checklist_skill: str | None
    letter_doc_id: str | None
    status: Literal["running", "completed", "failed"]
    started: datetime
    counts: CheckCounts | None = None
    signed_off: SignOff | None = None


class CaseSummary(Model):
    case_id: str
    label: str
    created: datetime
    data_class: DataClass
    documents: int
    checks: list[CheckBrief]


class CaseDetail(Model):
    manifest: Manifest
    checks: list[CheckBrief]


class ChecklistView(Model):
    skill: str
    visa: str | None = None
    version: str | None = None
    owner: str | None = None
    items: list[SpecItem] = Field(default_factory=list[SpecItem])
    error: str | None = None


class StartCheck(Model):
    kind: CheckKind
    checklist_skill: str | None = None
    letter_doc_id: str | None = None  # kind letter: an uploaded INZ letter (§8.8)


class CheckStarted(Model):
    check_id: str


class CheckView(Model):
    check_id: str
    case_id: str
    kind: CheckKind
    status: Literal["running", "completed", "failed"]
    state: CheckState | None = None
    result: CheckResult | None = None
    review: dict[str, ReviewAction] = Field(default_factory=dict[str, ReviewAction])
    notes: dict[str, str] = Field(default_factory=dict[str, str])
    blockers: list[str] = Field(default_factory=list[str])
    signed_off: SignOff | None = None
    error: str | None = None
    # kind letter: Monday-Friday days from today (New Zealand) to the letter's deadline,
    # negative once passed; public holidays are not counted out
    deadline_working_days: int | None = None


class ReviewIn(Model):
    action: ReviewAction
    note: str | None = None
    adviser: str


class SignOffIn(Model):
    adviser: str


# --- agent runs, context, memory, skills (design §11) -----------------------------------------


class StartRun(Model):
    task: str = Field(min_length=1, max_length=20_000)
    max_steps: int | None = Field(default=None, ge=1, le=20)


class RunStarted(Model):
    run_id: str


class RunBrief(Model):
    run_id: str
    task: str
    status: RunStatus
    started: datetime | None


class ContextPreview(Model):
    prompt: str
    breakdown: ContextBreakdown


class MemoryEntry(Model):
    slug: str
    title: str
    type: str
    description: str
    created: date | None
    usage: UsageEntry


class IndexBudget(Model):
    tokens: int
    budget: int
    over: bool


class MemoryList(Model):
    entries: list[MemoryEntry]
    budget: IndexBudget
    broken: list[str]


class MemoryDetail(Model):
    slug: str
    text: str
    body: str
    changelog: list[ChangeEntry]


class SkillReference(Model):
    path: str
    chars: int


class SkillEntry(Model):
    name: str
    description: str
    source: str
    read_only: bool
    body_chars: int
    references: list[SkillReference]


class SkillDetail(SkillEntry):
    body: str


class CleanupBrief(Model):
    workflow_id: str
    status: CleanupStatus
    started: datetime | None
    expires: datetime | None
    changes: int  # proposed changes awaiting (or past) review


class Accepted(Model):
    status: Literal["accepted"] = "accepted"
