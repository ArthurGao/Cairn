"""Case store file shapes (design §4.7-§4.10) and the inputs code validates (§8.3-§8.5)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

DataClass = Literal["synthetic", "client"]
PageMethod = Literal["text", "transcribed", "unreadable"]
DocStatus = Literal["pending", "ingested", "failed"]
CheckKind = Literal["consistency", "presubmission"]
ItemStatus = Literal["checked", "pending", "unable"]
Downgrade = Literal["missing", "no_valid_citation", "call_failed"]
ReviewAction = Literal["confirmed", "dismissed", "resolved", "reopened"]
AuditAction = ReviewAction | Literal["signed_off"]
Origin = Literal["rule", "model"]


# --- §4.7 manifest -------------------------------------------------------------------------


class PageRef(BaseModel):
    n: int
    method: PageMethod


class Document(BaseModel):
    doc_id: str
    filename: str
    stored_name: str  # originals/<stored_name>: "<doc_id>.<ext>" from the sniffed type
    media_type: str
    bytes: int
    sha256: str
    uploaded: datetime
    status: DocStatus = "pending"
    error: str | None = None
    pages: list[PageRef] = Field(default_factory=list[PageRef])


class Manifest(BaseModel):
    case_id: str
    label: str
    created: datetime
    data_class: DataClass
    documents: list[Document] = Field(default_factory=list[Document])

    def document(self, doc_id: str) -> Document | None:
        return next((d for d in self.documents if d.doc_id == doc_id), None)


# --- §4.8 page ------------------------------------------------------------------------------


class Page(BaseModel):
    doc_id: str
    page: int
    method: PageMethod
    source_sha256: str
    model: str | None = None
    reason: str | None = None
    text: str = ""


# --- model output that code validates (§8.3-§8.5) --------------------------------------------


class RawFact(BaseModel):
    """One fact as `case.extract_facts` returns it, before validation."""

    category: str
    subject: str
    qualifier: str | None = None
    value: str
    normalised: str
    page: int
    quote: str


class ModelConflict(BaseModel):
    fact_ids: list[str]
    summary: str
    question: str


class Citation(BaseModel):
    doc_id: str
    page: int
    quote: str


class ItemReply(BaseModel):
    item_id: str
    status: ItemStatus
    finding: str
    citations: list[Citation] = Field(default_factory=list[Citation])


# --- §4.9 check result ----------------------------------------------------------------------


class Fact(RawFact):
    """A RawFact that passed validation, with its id and document."""

    fact_id: str
    doc_id: str


class Conflict(BaseModel):
    finding_id: str
    fact_ids: list[str]
    origin: list[Origin]
    summary: str
    question: str
    drafted_by: Literal["model", "template"]


class ItemResult(BaseModel):
    finding_id: str
    item_id: str
    status: ItemStatus
    finding: str
    citations: list[Citation] = Field(default_factory=list[Citation])
    downgraded: Downgrade | None = None


class Gap(BaseModel):
    """A document or pages that could not be checked; reviewed like any other finding."""

    finding_id: str
    doc_id: str
    kind: Literal["unreadable", "failed"]
    pages: list[int] = Field(default_factory=list[int])
    reason: str


class Dropped(BaseModel):
    reason: str
    detail: str


class Coverage(BaseModel):
    documents: int
    documents_failed: int
    pages: int
    pages_transcribed: int
    pages_unreadable: int
    facts_accepted: int = 0
    facts_dropped: int = 0


class CallRecord(BaseModel):
    role: str
    vendor: str
    model: str
    tokens_in: int
    tokens_out: int
    prompt_version: str = ""


class ChecklistRef(BaseModel):
    skill: str
    version: str


class CheckResult(BaseModel):
    check_id: str
    case_id: str
    kind: CheckKind
    checklist: ChecklistRef | None = None
    started: datetime
    finished: datetime
    status: Literal["completed", "failed"]
    error: str | None = None
    coverage: Coverage
    facts: list[Fact] = Field(default_factory=list[Fact])
    conflicts: list[Conflict] = Field(default_factory=list[Conflict])
    items: list[ItemResult] = Field(default_factory=list[ItemResult])
    gaps: list[Gap] = Field(default_factory=list[Gap])
    dropped: list[Dropped] = Field(default_factory=list[Dropped])
    wording_replacements: int = 0
    calls: list[CallRecord] = Field(default_factory=list[CallRecord])

    def finding_ids(self) -> list[str]:
        return (
            [c.finding_id for c in self.conflicts]
            + [i.finding_id for i in self.items]
            + [g.finding_id for g in self.gaps]
        )


# --- §4.10 audit ----------------------------------------------------------------------------


class AuditEntry(BaseModel):
    at: datetime
    check_id: str
    finding_id: str | None
    action: AuditAction
    note: str | None = None
    adviser: str
