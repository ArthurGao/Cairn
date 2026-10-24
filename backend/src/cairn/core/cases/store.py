"""The case store on disk (design §3.2, §4.7-§4.10).

Every write holds the case's `.case.lock` and replaces files atomically, so readers (the API)
take no lock and never see a half-written file.
"""

import hashlib
import re
from collections.abc import Generator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import yaml
from filelock import FileLock

from cairn.core.atomic import append_line_durable, write_bytes_atomic, write_text_atomic
from cairn.core.cases.models import (
    AuditEntry,
    CheckResult,
    DataClass,
    DocStatus,
    Document,
    Manifest,
    Page,
    PageRef,
    ReviewAction,
)
from cairn.core.cases.sniff import sniff
from cairn.errors import Conflict, Invalid, NotFound, TooLarge

LOCK_TIMEOUT_S = 10
_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
SETTLED: frozenset[ReviewAction] = frozenset({"confirmed", "dismissed", "resolved"})


@dataclass(frozen=True)
class CaseLimits:
    max_documents: int
    max_file_bytes: int


def _safe_id(value: str, what: str) -> str:
    """Ids become path parts, so only plain ids pass (no separators, dots or traversal)."""
    if not _ID.match(value):
        raise Invalid(f"{what} {value!r} is not a valid id", code="invalid_id")
    return value


def case_dir(cases_dir: Path, case_id: str) -> Path:
    return cases_dir / _safe_id(case_id, "case id")


@contextmanager
def _locked(cases_dir: Path, case_id: str) -> Generator[Path]:
    root = case_dir(cases_dir, case_id)
    with FileLock(root / ".case.lock", timeout=LOCK_TIMEOUT_S):
        yield root


# --- manifest -------------------------------------------------------------------------------


def _save_manifest(root: Path, manifest: Manifest) -> None:
    write_text_atomic(root / "case.json", manifest.model_dump_json(indent=2) + "\n")


def load_manifest(cases_dir: Path, case_id: str) -> Manifest:
    path = case_dir(cases_dir, case_id) / "case.json"
    if not path.is_file():
        raise NotFound(f"case {case_id} does not exist", code="case_not_found")
    return Manifest.model_validate_json(path.read_text(encoding="utf-8"))


def list_cases(cases_dir: Path) -> list[Manifest]:
    manifests = [
        Manifest.model_validate_json(p.read_text(encoding="utf-8"))
        for p in cases_dir.glob("*/case.json")
    ]
    return sorted(manifests, key=lambda m: m.created, reverse=True)


def create_case(
    cases_dir: Path, case_id: str, label: str, data_class: DataClass, now: datetime
) -> Manifest:
    root = case_dir(cases_dir, case_id)
    if root.exists():
        raise Conflict(f"case {case_id} already exists", code="case_exists")
    root.mkdir(parents=True)
    manifest = Manifest(case_id=case_id, label=label, created=now, data_class=data_class)
    with _locked(cases_dir, case_id):
        _save_manifest(root, manifest)
    return manifest


def add_document(
    cases_dir: Path,
    case_id: str,
    doc_id: str,
    filename: str,
    data: bytes,
    now: datetime,
    limits: CaseLimits,
) -> Document:
    """Store an upload byte-for-byte as `originals/<doc_id>.<ext>` and list it as pending.

    Idempotent per `doc_id`: repeating the same upload returns the stored document.
    """
    _safe_id(doc_id, "document id")
    if len(data) > limits.max_file_bytes:
        raise TooLarge(f"{filename} is {len(data)} bytes; the limit is {limits.max_file_bytes}")
    media_type, ext = sniff(filename, data)
    sha256 = hashlib.sha256(data).hexdigest()
    with _locked(cases_dir, case_id) as root:
        manifest = load_manifest(cases_dir, case_id)
        if existing := manifest.document(doc_id):
            if existing.sha256 != sha256:
                raise Conflict(f"document {doc_id} already exists", code="document_exists")
            return existing
        if len(manifest.documents) >= limits.max_documents:
            raise TooLarge(f"case {case_id} already has {limits.max_documents} documents")
        document = Document(
            doc_id=doc_id,
            filename=filename,
            stored_name=f"{doc_id}.{ext}",
            media_type=media_type,
            bytes=len(data),
            sha256=sha256,
            uploaded=now,
        )
        write_bytes_atomic(root / "originals" / document.stored_name, data)
        manifest.documents.append(document)
        _save_manifest(root, manifest)
    return document


def original_path(cases_dir: Path, case_id: str, doc_id: str) -> Path:
    document = load_manifest(cases_dir, case_id).document(doc_id)
    if document is None:
        raise NotFound(f"document {doc_id} is not in case {case_id}", code="document_not_found")
    return case_dir(cases_dir, case_id) / "originals" / document.stored_name


def set_document_ingest(
    cases_dir: Path,
    case_id: str,
    doc_id: str,
    status: DocStatus,
    pages: list[PageRef],
    error: str | None = None,
) -> Document:
    with _locked(cases_dir, case_id) as root:
        manifest = load_manifest(cases_dir, case_id)
        document = manifest.document(doc_id)
        if document is None:
            raise NotFound(f"document {doc_id} is not in case {case_id}", code="document_not_found")
        document.status, document.pages, document.error = status, pages, error
        _save_manifest(root, manifest)
    return document


# --- pages (§4.8) ---------------------------------------------------------------------------


def _page_path(root: Path, doc_id: str, n: int) -> Path:
    return root / "pages" / _safe_id(doc_id, "document id") / f"p{n:04d}.md"


def write_pages(cases_dir: Path, case_id: str, pages: Sequence[Page]) -> None:
    """Write a document's page files under one lock; rewriting a page replaces it."""
    with _locked(cases_dir, case_id) as root:
        for page in pages:
            front = page.model_dump(exclude={"text"})
            body = "---\n" + yaml.safe_dump(front, sort_keys=False) + "---\n\n" + page.text
            write_text_atomic(_page_path(root, page.doc_id, page.page), body)


def read_page(cases_dir: Path, case_id: str, doc_id: str, n: int) -> Page:
    path = _page_path(case_dir(cases_dir, case_id), doc_id, n)
    if not path.is_file():
        raise NotFound(f"{doc_id} has no page {n}", code="page_not_found")
    _, front, body = path.read_text(encoding="utf-8").split("---\n", 2)
    return Page(**yaml.safe_load(front), text=body.removeprefix("\n"))


# --- results (§4.9) -------------------------------------------------------------------------


def write_result(cases_dir: Path, result: CheckResult) -> None:
    """Write a check result once; results are immutable (review lives in the audit log).

    Writing the identical result again is a no-op, so a retried activity succeeds.
    """
    text = result.model_dump_json(indent=2) + "\n"
    with _locked(cases_dir, result.case_id) as root:
        path = root / "checks" / f"{_safe_id(result.check_id, 'check id')}.json"
        if path.exists():
            if path.read_text(encoding="utf-8") == text:
                return
            raise Conflict(f"check {result.check_id} already has a result", code="result_exists")
        write_text_atomic(path, text)


def read_result(cases_dir: Path, case_id: str, check_id: str) -> CheckResult:
    path = case_dir(cases_dir, case_id) / "checks" / f"{_safe_id(check_id, 'check id')}.json"
    if not path.is_file():
        raise NotFound(f"check {check_id} has no result", code="check_not_found")
    return CheckResult.model_validate_json(path.read_text(encoding="utf-8"))


# --- audit (§4.10) --------------------------------------------------------------------------


def read_audit(cases_dir: Path, case_id: str) -> list[AuditEntry]:
    path = case_dir(cases_dir, case_id) / "_audit.jsonl"
    if not path.is_file():
        return []
    return [
        AuditEntry.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def review_states(audit: list[AuditEntry], check_id: str) -> dict[str, ReviewAction]:
    """Each finding's current review state: its last review action."""
    states: dict[str, ReviewAction] = {}
    for entry in audit:
        if entry.check_id == check_id and entry.finding_id and entry.action != "signed_off":
            states[entry.finding_id] = entry.action
    return states


def needs_review(result: CheckResult) -> list[str]:
    """Findings an adviser must settle before sign-off; a `checked` item does not need it."""
    checked = {i.finding_id for i in result.items if i.status == "checked"}
    return [f for f in result.finding_ids() if f not in checked]


def signoff_blockers(result: CheckResult, audit: list[AuditEntry]) -> list[str]:
    states = review_states(audit, result.check_id)
    return [f for f in needs_review(result) if states.get(f) not in SETTLED]


def _append(root: Path, entry: AuditEntry) -> None:
    append_line_durable(root / "_audit.jsonl", entry.model_dump_json())


def record_review(
    cases_dir: Path,
    result: CheckResult,
    finding_id: str,
    action: ReviewAction,
    note: str | None,
    adviser: str,
    now: datetime,
) -> AuditEntry:
    if finding_id not in result.finding_ids():
        raise NotFound(
            f"check {result.check_id} has no finding {finding_id}", code="unknown_finding"
        )
    if action == "dismissed" and not (note or "").strip():
        raise Invalid("dismissing a finding needs a note saying why", code="note_required")
    entry = AuditEntry(
        at=now,
        check_id=result.check_id,
        finding_id=finding_id,
        action=action,
        note=note,
        adviser=_adviser(adviser),
    )
    with _locked(cases_dir, result.case_id) as root:
        _append(root, entry)
    return entry


def _adviser(name: str) -> str:
    if not name.strip():
        raise Invalid("the adviser's name is required", code="adviser_required")
    return name.strip()


def sign_off(cases_dir: Path, result: CheckResult, adviser: str, now: datetime) -> AuditEntry:
    adviser = _adviser(adviser)
    with _locked(cases_dir, result.case_id) as root:
        blockers = signoff_blockers(result, read_audit(cases_dir, result.case_id))
        if blockers:
            raise Conflict(
                f"settle these findings first: {', '.join(blockers)}", code="signoff_blocked"
            )
        entry = AuditEntry(
            at=now,
            check_id=result.check_id,
            finding_id=None,
            action="signed_off",
            adviser=adviser,
        )
        _append(root, entry)
    return entry
