"""Case store file shapes (design §4.7-§4.10) and the inputs code validates (§8.3-§8.5)."""

from datetime import date, datetime
from typing import Literal

from pydantic import Field

from cairn.core.model import Model

DataClass = Literal["synthetic", "client"]
PageMethod = Literal["text", "transcribed", "unreadable"]
DocStatus = Literal["pending", "ingested", "failed"]
CheckKind = Literal["consistency", "presubmission", "letter"]
DocSource = Literal["client", "inz"]  # inz: a letter from INZ, never evidence (§8.8)
EvidenceStatus = Literal["supported", "partial", "no_evidence", "unable"]
DeadlineStatus = Literal["verified", "unverified", "missing"]
ItemStatus = Literal["checked", "pending", "unable"]
Downgrade = Literal["missing", "no_valid_citation", "call_failed"]
ReviewAction = Literal["confirmed", "dismissed", "resolved", "reopened"]
AuditAction = ReviewAction | Literal["signed_off"]
Origin = Literal["rule", "model"]


# --- §4.7 manifest -------------------------------------------------------------------------


class PageRef(Model):
    n: int
    method: PageMethod


class Document(Model):
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
    source: DocSource = "client"


class Manifest(Model):
    case_id: str
    label: str
    created: datetime
    data_class: DataClass
    documents: list[Document] = Field(default_factory=list[Document])

    def document(self, doc_id: str) -> Document | None:
        return next((d for d in self.documents if d.doc_id == doc_id), None)


# --- §4.8 page ------------------------------------------------------------------------------


class Page(Model):
    doc_id: str
    page: int
    method: PageMethod
    source_sha256: str
    model: str | None = None
    reason: str | None = None
    text: str = ""


# --- model output that code validates (§8.3-§8.5) --------------------------------------------


class RawFact(Model):
    """One fact as `case.extract_facts` returns it, before validation."""

    category: str
    subject: str
    qualifier: str | None = None
    value: str
    normalised: str
    page: int
    quote: str


class ModelConflict(Model):
    fact_ids: list[str]
    summary: str
    question: str


class Citation(Model):
    doc_id: str
    page: int
    quote: str


class ItemReply(Model):
    item_id: str
    status: ItemStatus
    finding: str
    citations: list[Citation] = Field(default_factory=list[Citation])


class RawDeadline(Model):
    """The reply deadline as `case.read_letter` reads it: an ISO date and its quote."""

    date: str
    quote: str
    page: int


class RawConcern(Model):
    summary: str
    passages: list[str]
    quote: str
    page: int


class LetterReading(Model):
    """`case.read_letter`'s reply before validation (§8.8)."""

    deadline: RawDeadline | None = None
    concerns: list[RawConcern] = Field(default_factory=list[RawConcern])
    context_passages: list[str] = Field(default_factory=list[str])


class EvidenceReply(Model):
    """`case.match_evidence`'s reply for one concern, before validation (§8.8)."""

    concern_id: str
    status: EvidenceStatus
    finding: str
    citations: list[Citation] = Field(default_factory=list[Citation])
    client_request: str | None = None
    conflict_ids: list[str] = Field(default_factory=list[str])


# --- §4.9 check result ----------------------------------------------------------------------


class Fact(RawFact):
    """A RawFact that passed validation, with its id and document."""

    fact_id: str
    doc_id: str


class Conflict(Model):
    finding_id: str
    fact_ids: list[str]
    origin: list[Origin]
    summary: str
    question: str
    drafted_by: Literal["model", "template"]


class ItemResult(Model):
    finding_id: str
    item_id: str
    status: ItemStatus
    finding: str
    citations: list[Citation] = Field(default_factory=list[Citation])
    downgraded: Downgrade | None = None


class Gap(Model):
    """A document or pages that could not be checked; reviewed like any other finding."""

    finding_id: str
    doc_id: str
    kind: Literal["unreadable", "failed"]
    pages: list[int] = Field(default_factory=list[int])
    reason: str


class Passage(Model):
    """A numbered stretch of the letter's text; every one must be accounted for (§8.8)."""

    passage_id: str
    page: int
    text: str


class Deadline(Model):
    finding_id: str = "d1"
    status: DeadlineStatus
    due: date | None = None
    quote: str | None = None
    page: int | None = None


class LetterConcern(Model):
    """One INZ concern as read from the letter, validated, before evidence is matched."""

    finding_id: str
    summary: str
    passages: list[str]
    page: int
    quote: str


class Concern(LetterConcern):
    status: EvidenceStatus
    finding: str
    citations: list[Citation] = Field(default_factory=list[Citation])
    client_request: str | None = None
    conflict_ids: list[str] = Field(default_factory=list[str])
    downgraded: Downgrade | None = None


class Unaccounted(Model):
    """A passage the model put in no concern and not in the context list."""

    finding_id: str
    passage_id: str
    page: int
    text: str


class LetterResult(Model):
    doc_id: str
    related_check_id: str | None = None  # the consistency check whose conflicts were offered
    deadline: Deadline
    concerns: list[Concern] = Field(default_factory=list[Concern])
    unaccounted: list[Unaccounted] = Field(default_factory=list[Unaccounted])
    client_email: str = ""
    reply_outline: str = ""


class Dropped(Model):
    reason: str
    detail: str


class LetterRead(Model):
    """The letter's validated reading, before evidence is matched (§8.8)."""

    deadline: Deadline
    concerns: list[LetterConcern]
    unaccounted: list[Unaccounted]
    dropped: list[Dropped]
    replaced: int = 0


class Coverage(Model):
    documents: int
    documents_failed: int
    pages: int
    pages_transcribed: int
    pages_unreadable: int
    facts_accepted: int = 0
    facts_dropped: int = 0


class CallRecord(Model):
    role: str
    vendor: str
    model: str
    tokens_in: int
    tokens_out: int
    prompt_version: str = ""


class ChecklistRef(Model):
    skill: str
    version: str


class CheckResult(Model):
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
    letter: LetterResult | None = None
    dropped: list[Dropped] = Field(default_factory=list[Dropped])
    wording_replacements: int = 0
    calls: list[CallRecord] = Field(default_factory=list[CallRecord])

    def finding_ids(self) -> list[str]:
        letter: list[str] = []
        if self.letter:
            letter = [
                self.letter.deadline.finding_id,
                *(c.finding_id for c in self.letter.concerns),
                *(u.finding_id for u in self.letter.unaccounted),
            ]
        return (
            [c.finding_id for c in self.conflicts]
            + [i.finding_id for i in self.items]
            + letter
            + [g.finding_id for g in self.gaps]
        )


class CheckStart(Model):
    """Written by the API when it starts a check, so a running check is listed before its
    result exists (`checks/<check_id>.start.json`)."""

    check_id: str
    kind: CheckKind
    checklist_skill: str | None = None
    letter_doc_id: str | None = None
    started: datetime


# --- §4.10 audit ----------------------------------------------------------------------------


class AuditEntry(Model):
    at: datetime
    check_id: str
    finding_id: str | None
    action: AuditAction
    note: str | None = None
    adviser: str
