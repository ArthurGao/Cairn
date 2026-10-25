"""Case routes (design §11): cases, uploads, pages, checks, review and sign-off."""

from datetime import UTC, date, datetime
from io import BytesIO
from typing import Annotated, Any
from zoneinfo import ZoneInfo

import pypdfium2 as pdfium
from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse, Response
from PIL import Image
from temporalio.client import WorkflowExecutionStatus
from temporalio.service import RPCError
from ulid import ULID

from cairn.api.schemas import (
    CaseCreate,
    CaseCreated,
    CaseDetail,
    CaseSummary,
    CheckBrief,
    CheckCounts,
    ChecklistView,
    CheckStarted,
    CheckView,
    ErrorResponse,
    ReviewIn,
    SignOff,
    SignOffIn,
    StartCheck,
)
from cairn.api.services import Services, services
from cairn.core.cases import store
from cairn.core.cases.coverage import check_counts
from cairn.core.cases.letters import require_letter, working_days_until
from cairn.core.cases.models import (
    AuditEntry,
    CheckResult,
    CheckStart,
    DocSource,
    Document,
    Page,
)
from cairn.core.cases.spec import list_checklists, require_checklist
from cairn.errors import Invalid, NotFound, TooLarge
from cairn.workflows.case_check import CaseCheckWorkflow
from cairn.workflows.case_models import CheckInput, CheckState, SpecItem, check_workflow_id

router = APIRouter(prefix="/api", tags=["cases"])
Deps = Annotated[Services, Depends(services)]
ERRORS: dict[int | str, dict[str, Any]] = {
    code: {"model": ErrorResponse} for code in (404, 409, 413, 415, 422, 503)
}
MAX_RENDER_PIXELS = 25_000_000


def _now() -> datetime:
    return datetime.now(UTC)


def _today(tz: str) -> date:
    """Today where the advisers are (`settings.tz`): INZ deadlines are New Zealand dates."""
    return _now().astimezone(ZoneInfo(tz)).date()


def _counts(result: CheckResult) -> CheckCounts:
    return CheckCounts.model_validate(check_counts(result))


def _sign_off(audit: list[AuditEntry], check_id: str) -> SignOff | None:
    entry = store.signed_off(audit, check_id)
    return SignOff(adviser=entry.adviser, at=entry.at) if entry else None


def _briefs(deps: Services, case_id: str) -> list[CheckBrief]:
    audit = store.read_audit(deps.settings.cases_dir, case_id)
    return [
        CheckBrief(
            check_id=start.check_id,
            kind=start.kind,
            checklist_skill=start.checklist_skill,
            letter_doc_id=start.letter_doc_id,
            status=result.status if result else "running",
            started=start.started,
            counts=_counts(result) if result else None,
            signed_off=_sign_off(audit, start.check_id),
        )
        for start, result in store.list_checks(deps.settings.cases_dir, case_id)
    ]


@router.post(
    "/cases",
    status_code=201,
    response_model=CaseCreated,
    responses=ERRORS,
    operation_id="createCase",
)
def create_case(body: CaseCreate, deps: Deps) -> CaseCreated:
    case_id = str(ULID())
    store.create_case(
        deps.settings.cases_dir, case_id, body.label.strip(), deps.settings.data_class, _now()
    )
    return CaseCreated(case_id=case_id)


@router.get("/cases", response_model=list[CaseSummary], operation_id="listCases")
def list_cases(deps: Deps) -> list[CaseSummary]:
    return [
        CaseSummary(
            case_id=m.case_id,
            label=m.label,
            created=m.created,
            data_class=m.data_class,
            documents=len(m.documents),
            checks=_briefs(deps, m.case_id),
        )
        for m in store.list_cases(deps.settings.cases_dir)
    ]


@router.get("/cases/{case_id}", response_model=CaseDetail, responses=ERRORS, operation_id="getCase")
def get_case(case_id: str, deps: Deps) -> CaseDetail:
    manifest = store.load_manifest(deps.settings.cases_dir, case_id)
    return CaseDetail(manifest=manifest, checks=_briefs(deps, case_id))


@router.post(
    "/cases/{case_id}/documents",
    status_code=201,
    response_model=list[Document],
    responses=ERRORS,
    operation_id="uploadDocuments",
)
async def upload_documents(
    case_id: str,
    deps: Deps,
    files: Annotated[list[UploadFile], File()],
    source: Annotated[DocSource, Form()] = "client",
) -> list[Document]:
    settings = deps.settings
    limits = store.CaseLimits(
        max_documents=settings.max_documents_per_case,
        max_file_bytes=settings.max_upload_mb * 1024 * 1024,
    )
    store.load_manifest(settings.cases_dir, case_id)  # 404 before reading any upload
    if len(files) > limits.max_documents:
        raise TooLarge(f"at most {limits.max_documents} files per case")
    documents: list[Document] = []
    for upload in files:
        data = await upload.read(limits.max_file_bytes + 1)  # never read more than the limit
        if len(data) > limits.max_file_bytes:
            raise TooLarge(f"{upload.filename} is over {settings.max_upload_mb} MB")
        documents.append(
            store.add_document(
                settings.cases_dir,
                case_id,
                str(ULID()),
                upload.filename or "upload",
                data,
                _now(),
                limits,
                source,
            )
        )
    return documents


@router.get(
    "/cases/{case_id}/documents/{doc_id}/original",
    response_class=FileResponse,
    responses=ERRORS,
    operation_id="getOriginal",
)
def get_original(case_id: str, doc_id: str, deps: Deps) -> FileResponse:
    manifest = store.load_manifest(deps.settings.cases_dir, case_id)
    document = manifest.document(doc_id)
    if document is None:
        raise NotFound(f"document {doc_id} is not in case {case_id}", code="document_not_found")
    path = store.original_path(deps.settings.cases_dir, case_id, doc_id)
    return FileResponse(path, media_type=document.media_type, filename=document.filename)


@router.get(
    "/cases/{case_id}/documents/{doc_id}/pages/{n}",
    response_model=Page,
    responses=ERRORS,
    operation_id="getPage",
)
def get_page(case_id: str, doc_id: str, n: int, deps: Deps) -> Page:
    return store.read_page(deps.settings.cases_dir, case_id, doc_id, n)


@router.get(
    "/cases/{case_id}/documents/{doc_id}/pages/{n}/render",
    response_class=Response,
    responses={**ERRORS, 200: {"content": {"image/png": {}}}},
    operation_id="renderPage",
)
def render_page(case_id: str, doc_id: str, n: int, deps: Deps) -> Response:
    """A server-side PNG of the page; the browser never opens the original PDF (§13)."""
    manifest = store.load_manifest(deps.settings.cases_dir, case_id)
    document = manifest.document(doc_id)
    if document is None or n < 1:
        raise NotFound(f"no page {n} of {doc_id}", code="page_not_found")
    data = store.original_path(deps.settings.cases_dir, case_id, doc_id).read_bytes()
    buffer = BytesIO()
    if document.media_type == "application/pdf":
        pdf = pdfium.PdfDocument(data)
        if n > len(pdf):
            raise NotFound(f"no page {n} of {doc_id}", code="page_not_found")
        page = pdf[n - 1]
        width, height = page.get_size()
        if width * height > MAX_RENDER_PIXELS:
            raise Invalid("this page is too large to render", code="not_renderable")
        page.render(scale=1 if width * height * 4 > MAX_RENDER_PIXELS else 2).to_pil().save(
            buffer, format="PNG"
        )
    elif document.media_type.startswith("image/") and n == 1:
        image = Image.open(BytesIO(data))  # lazy: the size is known before decoding pixels
        if image.width * image.height > MAX_RENDER_PIXELS:
            raise Invalid("this image is too large to render", code="not_renderable")
        image.save(buffer, format="PNG")
    else:
        raise Invalid(f"{document.filename} has no image to render", code="not_renderable")
    return Response(buffer.getvalue(), media_type="image/png")


@router.get("/checklists", response_model=list[ChecklistView], operation_id="listChecklists")
def checklists(deps: Deps) -> list[ChecklistView]:
    return [
        ChecklistView(
            skill=info.skill,
            visa=info.checklist.visa if info.checklist else None,
            version=info.checklist.version if info.checklist else None,
            owner=info.checklist.owner if info.checklist else None,
            items=[
                SpecItem(id=i.id, requirement=i.requirement, verify=i.verify)
                for i in (info.checklist.items if info.checklist else ())
            ],
            error=info.error,
        )
        for info in list_checklists(deps.settings.home / "skills")
    ]


@router.post(
    "/cases/{case_id}/checks",
    status_code=202,
    response_model=CheckStarted,
    responses=ERRORS,
    operation_id="startCheck",
)
async def start_check(case_id: str, body: StartCheck, deps: Deps) -> CheckStarted:
    settings = deps.settings
    manifest = store.load_manifest(settings.cases_dir, case_id)
    if not manifest.documents:
        raise Invalid("upload at least one document before running a check", code="case_empty")
    if body.kind == "presubmission":
        require_checklist(settings.home / "skills", body.checklist_skill)
    if body.kind == "letter":
        require_letter(manifest, body.letter_doc_id)
    client = await deps.temporal.client()
    check_id = str(ULID())
    check = CheckInput(
        check_id=check_id,
        case_id=case_id,
        kind=body.kind,
        checklist_skill=body.checklist_skill if body.kind == "presubmission" else None,
        letter_doc_id=body.letter_doc_id if body.kind == "letter" else None,
        map_budget=settings.map_budget,
        case_context_budget=settings.case_context_budget,
        min_page_chars=settings.min_page_chars,
        concurrency=settings.check_concurrency,
        item_batch_size=settings.item_batch_size,
        max_pages_per_case=settings.max_pages_per_case,
    )
    # The start record first: a check that then fails to start is listed and reported as
    # failed, never orphaned in Temporal with nothing pointing at it.
    store.record_check_start(
        settings.cases_dir,
        case_id,
        CheckStart(
            check_id=check_id,
            kind=check.kind,
            checklist_skill=check.checklist_skill,
            letter_doc_id=check.letter_doc_id,
            started=_now(),
        ),
    )
    await client.start_workflow(
        CaseCheckWorkflow.run,
        check,
        id=check_workflow_id(check_id),
        task_queue=settings.task_queue,
    )
    return CheckStarted(check_id=check_id)


async def _running_state(deps: Services, check_id: str) -> tuple[CheckState | None, str | None]:
    """Progress of a check without a result yet; a stopped workflow is reported, not hidden."""
    client = await deps.temporal.client()
    handle = client.get_workflow_handle(check_workflow_id(check_id))
    try:
        description = await handle.describe()
        if description.status != WorkflowExecutionStatus.RUNNING:
            status = description.status.name.lower() if description.status else "unknown"
            return None, f"the check stopped without a result ({status})"
        state = await handle.query(CaseCheckWorkflow.get_state)
    except RPCError as exc:
        return None, f"the check cannot be found in Temporal: {exc.message}"
    return state, None


@router.get(
    "/cases/{case_id}/checks/{check_id}",
    response_model=CheckView,
    responses=ERRORS,
    operation_id="getCheck",
)
async def get_check(case_id: str, check_id: str, deps: Deps) -> CheckView:
    cases_dir = deps.settings.cases_dir
    start = store.read_check_start(cases_dir, case_id, check_id)
    try:
        result: CheckResult | None = store.read_result(cases_dir, case_id, check_id)
    except NotFound:
        result = None
    view = CheckView(check_id=check_id, case_id=case_id, kind=start.kind, status="running")
    if result is None:
        view.state, view.error = await _running_state(deps, check_id)
        if view.error:
            view.status = "failed"
        return view
    audit = store.read_audit(cases_dir, case_id)
    view.status, view.result, view.error = result.status, result, result.error
    view.review = store.review_states(audit, check_id)
    view.notes = store.review_notes(audit, check_id)
    view.blockers = store.signoff_blockers(result, audit)
    view.signed_off = _sign_off(audit, check_id)
    if result.letter and result.letter.deadline.due:
        today = _today(deps.settings.tz)
        view.deadline_working_days = working_days_until(result.letter.deadline.due, today)
    return view


@router.post(
    "/cases/{case_id}/checks/{check_id}/findings/{finding_id}/review",
    response_model=AuditEntry,
    responses=ERRORS,
    operation_id="reviewFinding",
)
def review_finding(
    case_id: str, check_id: str, finding_id: str, body: ReviewIn, deps: Deps
) -> AuditEntry:
    result = store.read_result(deps.settings.cases_dir, case_id, check_id)
    return store.record_review(
        deps.settings.cases_dir, result, finding_id, body.action, body.note, body.adviser, _now()
    )


@router.post(
    "/cases/{case_id}/checks/{check_id}/signoff",
    response_model=AuditEntry,
    responses=ERRORS,
    operation_id="signOff",
)
def sign_off(case_id: str, check_id: str, body: SignOffIn, deps: Deps) -> AuditEntry:
    result = store.read_result(deps.settings.cases_dir, case_id, check_id)
    return store.sign_off(deps.settings.cases_dir, result, body.adviser, _now())
