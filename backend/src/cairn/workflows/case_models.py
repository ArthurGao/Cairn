"""Inputs and outputs of `CaseCheckWorkflow` and its activities (design §8.1).

Payloads stay small: page text never crosses a workflow boundary; activities read and write
page files themselves and pass ids, counts and validated facts.
"""

from datetime import datetime
from typing import Literal

from pydantic import Field

from cairn.core.cases.models import (
    CallRecord,
    CheckKind,
    Dropped,
    Fact,
    ItemReply,
    ModelConflict,
)
from cairn.core.model import Model


def check_workflow_id(check_id: str) -> str:
    return f"check-{check_id}"


class CheckInput(Model):
    check_id: str
    case_id: str
    kind: CheckKind
    checklist_skill: str | None = None
    map_budget: int = 100_000
    case_context_budget: int = 150_000
    min_page_chars: int = 40
    concurrency: int = 4
    item_batch_size: int = 5
    max_pages_per_case: int = 500


Step = Literal[
    "starting", "ingesting", "extracting", "comparing", "checking", "writing", "done", "failed"
]


class CheckState(Model):
    """`get_state` query result: progress while the check runs."""

    check_id: str
    case_id: str
    kind: CheckKind
    step: Step = "starting"
    documents_total: int = 0
    documents_done: int = 0
    units_total: int = 0
    units_done: int = 0
    error: str | None = None


class SpecItem(Model):
    id: str
    requirement: str
    verify: str


class CheckSpec(Model):
    """What `load_check_spec` resolved: loaded by code, never chosen by the model (D-13)."""

    doc_ids: list[str]  # every document in the case, manifest order
    pending_doc_ids: list[str]  # not yet ingested
    checklist_version: str | None = None
    items: list[SpecItem] = Field(default_factory=list[SpecItem])


class IngestInput(Model):
    case_id: str
    doc_id: str
    min_page_chars: int
    max_pages_per_case: int


class IngestOutcome(Model):
    doc_id: str
    status: Literal["ingested", "failed"]
    pages: int
    error: str | None = None
    calls: list[CallRecord] = Field(default_factory=list[CallRecord])


class MarkFailedInput(Model):
    case_id: str
    doc_id: str
    error: str


class ExtractInput(Model):
    case_id: str
    doc_id: str
    map_budget: int


class ExtractOutcome(Model):
    doc_id: str
    facts: list[Fact]  # ids are local to the document (f1…); the workflow renumbers them
    dropped: list[Dropped]
    calls: list[CallRecord] = Field(default_factory=list[CallRecord])


class ProposeInput(Model):
    case_id: str
    facts: list[Fact]
    case_context_budget: int


class ProposeOutcome(Model):
    proposals: list[ModelConflict]
    calls: list[CallRecord] = Field(default_factory=list[CallRecord])


class ItemsInput(Model):
    case_id: str
    checklist_skill: str
    item_ids: list[str]


class ItemsOutcome(Model):
    replies: list[ItemReply]
    calls: list[CallRecord] = Field(default_factory=list[CallRecord])


class MeasureInput(Model):
    case_id: str
    budget: int


class FinishInput(Model):
    check: CheckInput
    started: datetime
    finished: datetime
    facts: list[Fact] = Field(default_factory=list[Fact])
    dropped: list[Dropped] = Field(default_factory=list[Dropped])
    proposals: list[ModelConflict] = Field(default_factory=list[ModelConflict])
    model_error: str | None = None
    replies: list[ItemReply] = Field(default_factory=list[ItemReply])
    failed_items: list[str] = Field(default_factory=list[str])
    extraction_failures: dict[str, str] = Field(default_factory=dict[str, str])
    calls: list[CallRecord] = Field(default_factory=list[CallRecord])
    error: str | None = None  # set: the check failed as a whole; no findings are written


class CheckSummary(Model):
    check_id: str
    status: Literal["completed", "failed"]
    error: str | None = None
    conflicts: int = 0
    checked: int = 0
    pending: int = 0
    unable: int = 0
    gaps: int = 0
    clean: bool = False
