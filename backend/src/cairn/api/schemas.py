"""API models; the OpenAPI source for the frontend's generated client."""

from datetime import datetime
from typing import Literal

from pydantic import Field

from cairn.core.cases.models import (
    CheckKind,
    CheckResult,
    DataClass,
    Manifest,
    ReviewAction,
)
from cairn.core.model import Model
from cairn.workflows.case_models import CheckState, SpecItem


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
    gaps: int = 0
    clean: bool = False


class CheckBrief(Model):
    check_id: str
    kind: CheckKind
    checklist_skill: str | None
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


class ReviewIn(Model):
    action: ReviewAction
    note: str | None = None
    adviser: str


class SignOffIn(Model):
    adviser: str
