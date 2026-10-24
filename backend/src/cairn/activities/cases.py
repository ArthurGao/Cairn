"""Activities of `CaseCheckWorkflow` (design §8). Every file and model call happens here.

Business rules come from `cairn.core.cases`; this module wires files, the LLM client and
Temporal together. Activities may run twice: ingest and result writing are idempotent.
"""

import base64
import json
from collections.abc import Sequence
from io import BytesIO
from pathlib import Path
from typing import Any

import pypdfium2 as pdfium
from PIL import Image
from pydantic import BaseModel, Field
from temporalio import activity
from temporalio.exceptions import ApplicationError

from cairn.activities.common import call_llm, fatal, parse_reply, permanent
from cairn.core.cases import store
from cairn.core.cases.coverage import build_coverage, build_gaps, is_clean
from cairn.core.cases.facts import (
    accept_model_conflicts,
    merge_conflicts,
    rule_baseline,
    validate_facts,
)
from cairn.core.cases.items import apply_item_rules, status_counts
from cairn.core.cases.models import (
    CallRecord,
    ChecklistRef,
    CheckResult,
    Document,
    Dropped,
    Fact,
    ItemReply,
    ModelConflict,
    Page,
    PageRef,
    RawFact,
)
from cairn.core.cases.spec import (
    CONSISTENCY_SKILL,
    Category,
    Checklist,
    SpecInvalid,
    load_categories,
    load_checklist,
    require_checklist,
)
from cairn.core.formats import parse_skill
from cairn.core.tokens import estimate_tokens
from cairn.errors import CairnError
from cairn.llm.client import LlmClient
from cairn.llm.prompts import load_prompt
from cairn.llm.roles import CHECK_ROLES, Role, data_class_problem
from cairn.llm.types import ImagePart, LlmRequest, LlmResult, Message, TextPart
from cairn.settings import Settings
from cairn.workflows.case_models import (
    CheckInput,
    CheckSpec,
    CheckSummary,
    ExtractInput,
    ExtractOutcome,
    FinishInput,
    IngestInput,
    IngestOutcome,
    ItemsInput,
    ItemsOutcome,
    MarkFailedInput,
    MeasureInput,
    ProposeInput,
    ProposeOutcome,
    SpecItem,
)

RENDER_SCALE = 2  # 144 dpi: enough for a model to read a scanned page
MAX_RENDER_PIXELS = 25_000_000  # larger renders risk memory exhaustion (a crafted PDF)


class _Transcription(BaseModel):
    readable: bool
    text: str = ""
    reason: str | None = None


class _Facts(BaseModel):
    facts: list[RawFact] = Field(default_factory=list[RawFact])


class _Conflicts(BaseModel):
    conflicts: list[ModelConflict] = Field(default_factory=list[ModelConflict])


class _Items(BaseModel):
    results: list[ItemReply] = Field(default_factory=list[ItemReply])


MAX_TOKENS = "max_tokens"  # ApplicationError type for a reply cut off at max_tokens


def _heartbeat() -> None:
    if activity.in_activity():
        activity.heartbeat()


def _page_block(doc_id: str, filename: str, n: int, text: str) -> str:
    return f"=== document {doc_id} ({filename}) | page {n} ===\n{text.strip()}\n"


class CaseActivities:
    def __init__(self, settings: Settings, client: LlmClient):
        self.settings = settings
        self.client = client

    @property
    def cases(self) -> Path:
        return self.settings.cases_dir

    @property
    def skills(self) -> Path:
        return self.settings.home / "skills"

    # --- model calls ------------------------------------------------------------------------

    async def _call(self, request: LlmRequest, calls: list[CallRecord]) -> LlmResult:
        result = await call_llm(self.client, request)
        calls.append(
            CallRecord(
                role=result.role,
                vendor=result.vendor,
                model=result.model,
                tokens_in=result.tokens_in,
                tokens_out=result.tokens_out,
                prompt_version=request.prompt_version,
            )
        )
        return result

    # --- spec and gate ----------------------------------------------------------------------

    def _skill_body(self, name: str) -> str:
        return parse_skill((self.skills / name / "SKILL.md").read_text(encoding="utf-8")).body

    def _categories(self) -> list[Category]:
        return load_categories(self.skills / CONSISTENCY_SKILL)

    def _checklist(self, skill: str) -> Checklist:
        return load_checklist(self.skills / skill)

    @activity.defn
    @permanent
    async def load_check_spec(self, check: CheckInput) -> CheckSpec:
        manifest = store.load_manifest(self.cases, check.case_id)
        if problem := data_class_problem(
            self.client.roles,
            manifest.data_class,
            self.settings.client_data_vendors,
            CHECK_ROLES[check.kind],
        ):
            raise fatal(problem, "data_class_blocked")
        spec = CheckSpec(
            doc_ids=[d.doc_id for d in manifest.documents],
            pending_doc_ids=[d.doc_id for d in manifest.documents if d.status == "pending"],
        )
        try:
            if check.kind == "consistency":
                self._categories()
            else:
                checklist = require_checklist(self.skills, check.checklist_skill)
                spec.checklist_version = checklist.version
                spec.items = [
                    SpecItem(id=i.id, requirement=i.requirement, verify=i.verify)
                    for i in checklist.items
                ]
        except (SpecInvalid, OSError) as exc:
            raise fatal(str(exc), "spec_invalid") from exc
        if not spec.doc_ids:
            raise fatal("the case has no documents", "case_empty")
        return spec

    # --- ingest (§8.2) ----------------------------------------------------------------------

    async def _transcribe(
        self, filename: str, n: int, png: bytes, sha256: str, doc_id: str, calls: list[CallRecord]
    ) -> Page:
        version, system = load_prompt("document_transcribe")
        request = LlmRequest(
            role=Role.DOCUMENT_TRANSCRIBE,
            system=system,
            messages=[
                Message.user(
                    f"Document: {filename} | page {n}",
                    ImagePart(data_b64=base64.b64encode(png).decode()),
                )
            ],
            output_schema=_Transcription.model_json_schema(),
            prompt_version=version,
        )
        result = await self._call(request, calls)
        out = parse_reply(_Transcription, result)
        if not out.readable:
            return Page(
                doc_id=doc_id,
                page=n,
                method="unreadable",
                source_sha256=sha256,
                model=result.model,
                reason=out.reason or "the model could not read the page",
            )
        return Page(
            doc_id=doc_id,
            page=n,
            method="transcribed",
            source_sha256=sha256,
            model=result.model,
            text=out.text,
        )

    @activity.defn
    @permanent
    async def ingest_document(self, job: IngestInput) -> IngestOutcome:
        manifest = store.load_manifest(self.cases, job.case_id)
        doc = manifest.document(job.doc_id)
        if doc is None:
            raise fatal(f"no document {job.doc_id}", "document_not_found")
        if doc.status == "ingested":  # a retried activity, or ingested by an earlier check
            return IngestOutcome(doc_id=doc.doc_id, status="ingested", pages=len(doc.pages))
        data = store.original_path(self.cases, job.case_id, doc.doc_id).read_bytes()
        others = sum(len(d.pages) for d in manifest.documents if d.doc_id != doc.doc_id)
        calls: list[CallRecord] = []
        pages: list[Page] = []

        def done_before(n: int) -> Page | None:
            """A page an earlier attempt of this activity already wrote (retry after a crash)."""
            try:
                page = store.read_page(self.cases, job.case_id, doc.doc_id, n)
            except CairnError:
                return None
            return page if page.source_sha256 == doc.sha256 else None

        def keep(page: Page) -> None:
            """Write each page as soon as it exists, so a retry does not redo it."""
            store.write_pages(self.cases, job.case_id, [page])
            pages.append(page)
            _heartbeat()

        def failed(error: str) -> IngestOutcome:
            store.set_document_ingest(self.cases, job.case_id, doc.doc_id, "failed", [], error)
            return IngestOutcome(doc_id=doc.doc_id, status="failed", pages=0, error=error)

        if doc.media_type == "application/pdf":
            try:
                pdf = pdfium.PdfDocument(data)
            except pdfium.PdfiumError as exc:
                return failed(f"{doc.filename} is not a readable PDF ({exc})")
            if others + len(pdf) > job.max_pages_per_case:
                return failed(
                    f"{doc.filename} has {len(pdf)} pages; the case limit is "
                    f"{job.max_pages_per_case} pages"
                )
            for index in range(len(pdf)):
                if earlier := done_before(index + 1):
                    pages.append(earlier)
                    continue
                page = pdf[index]
                text = page.get_textpage().get_text_range().replace("\r\n", "\n")
                if len(text.strip()) >= job.min_page_chars:
                    keep(
                        Page(
                            doc_id=doc.doc_id,
                            page=index + 1,
                            method="text",
                            source_sha256=doc.sha256,
                            text=text,
                        )
                    )
                    continue
                width, height = page.get_size()
                scale = next(
                    (s for s in (RENDER_SCALE, 1) if width * height * s * s <= MAX_RENDER_PIXELS),
                    None,
                )
                if scale is None:  # a render this size could exhaust memory; never guess
                    keep(
                        Page(
                            doc_id=doc.doc_id,
                            page=index + 1,
                            method="unreadable",
                            source_sha256=doc.sha256,
                            reason=f"page is too large to render ({width:.0f} x {height:.0f} pt)",
                        )
                    )
                    continue
                image = page.render(scale=scale).to_pil()
                buffer = BytesIO()
                image.save(buffer, format="PNG")
                keep(
                    await self._transcribe(
                        doc.filename, index + 1, buffer.getvalue(), doc.sha256, doc.doc_id, calls
                    )
                )
        elif doc.media_type.startswith("image/"):
            png = data
            if doc.media_type != "image/png":
                buffer = BytesIO()
                Image.open(BytesIO(data)).save(buffer, format="PNG")
                png = buffer.getvalue()
            keep(
                done_before(1)
                or await self._transcribe(doc.filename, 1, png, doc.sha256, doc.doc_id, calls)
            )
        else:  # text/plain, text/markdown
            keep(
                Page(
                    doc_id=doc.doc_id,
                    page=1,
                    method="text",
                    source_sha256=doc.sha256,
                    text=data.decode("utf-8"),
                )
            )
        refs = [PageRef(n=p.page, method=p.method) for p in pages]
        store.set_document_ingest(self.cases, job.case_id, doc.doc_id, "ingested", refs)
        return IngestOutcome(doc_id=doc.doc_id, status="ingested", pages=len(pages), calls=calls)

    @activity.defn
    @permanent
    async def mark_document_failed(self, job: MarkFailedInput) -> None:
        store.set_document_ingest(self.cases, job.case_id, job.doc_id, "failed", [], job.error)

    # --- consistency (§8.3, §8.4) -----------------------------------------------------------

    def _readable_pages(self, case_id: str, doc: Document) -> dict[int, str]:
        return {
            p.n: store.read_page(self.cases, case_id, doc.doc_id, p.n).text
            for p in doc.pages
            if p.method != "unreadable"
        }

    @staticmethod
    def _units(pages: dict[int, str], budget: int) -> list[list[int]]:
        """Consecutive page groups under the budget; every page in exactly one group."""
        units: list[list[int]] = []
        current: list[int] = []
        used = 0
        for n, text in sorted(pages.items()):
            cost = estimate_tokens(text)
            if current and used + cost > budget:
                units.append(current)
                current, used = [], 0
            current.append(n)
            used += cost
        if current:
            units.append(current)
        return units

    async def _extract_unit(
        self,
        doc_id: str,
        filename: str,
        pages: dict[int, str],
        unit: list[int],
        prompt: LlmRequest,
        calls: list[CallRecord],
        may_split: bool = True,
    ) -> list[RawFact]:
        body = "".join(_page_block(doc_id, filename, n, pages[n]) for n in unit)
        request = prompt.model_copy(
            update={"messages": [Message.user(f"Document: {filename} (id {doc_id})\n\n{body}")]}
        )
        try:
            result = await self._call(request, calls)
        except ApplicationError as exc:
            if exc.type == MAX_TOKENS and may_split and len(unit) > 1:
                half = len(unit) // 2
                return [
                    *await self._extract_unit(
                        doc_id, filename, pages, unit[:half], prompt, calls, False
                    ),
                    *await self._extract_unit(
                        doc_id, filename, pages, unit[half:], prompt, calls, False
                    ),
                ]
            raise
        return parse_reply(_Facts, result).facts

    @activity.defn
    @permanent
    async def extract_facts(self, job: ExtractInput) -> ExtractOutcome:
        doc = store.load_manifest(self.cases, job.case_id).document(job.doc_id)
        if doc is None:
            raise fatal(f"no document {job.doc_id}", "document_not_found")
        pages = self._readable_pages(job.case_id, doc)
        categories = self._categories()
        version, template = load_prompt("case_extract_facts")
        schema = _Facts.model_json_schema()
        schema["$defs"]["RawFact"]["properties"]["category"]["enum"] = [c.id for c in categories]
        prompt = LlmRequest(
            role=Role.CASE_EXTRACT_FACTS,
            system=template.format(
                categories=", ".join(f"{c.id} ({c.kind})" for c in categories),
                skill=self._skill_body(CONSISTENCY_SKILL),
            ),
            messages=[],
            output_schema=schema,
            prompt_version=version,
        )
        calls: list[CallRecord] = []
        facts: list[Fact] = []
        dropped: list[Dropped] = []
        for unit in self._units(pages, job.map_budget):
            raw = await self._extract_unit(doc.doc_id, doc.filename, pages, unit, prompt, calls)
            _heartbeat()
            accepted, rejected = validate_facts(
                doc.doc_id, raw, {n: pages[n] for n in unit}, categories, len(facts) + 1
            )
            facts += accepted
            dropped += rejected
        return ExtractOutcome(doc_id=doc.doc_id, facts=facts, dropped=dropped, calls=calls)

    @activity.defn
    @permanent
    async def propose_conflicts(self, job: ProposeInput) -> ProposeOutcome:
        manifest = store.load_manifest(self.cases, job.case_id)
        names = {d.doc_id: d.filename for d in manifest.documents}
        shown = {"fact_id", "page", "category", "subject", "qualifier", "value", "normalised"}
        lines = [
            json.dumps({"document": names.get(f.doc_id, f.doc_id), **f.model_dump(include=shown)})
            for f in job.facts
        ]
        text = "Facts:\n" + "\n".join(lines)
        if (tokens := estimate_tokens(text)) > job.case_context_budget:
            raise fatal(
                f"the facts need {tokens} tokens; the case budget is {job.case_context_budget}",
                "case_too_large_for_v1",
            )
        version, template = load_prompt("case_compare_facts")
        request = LlmRequest(
            role=Role.CASE_COMPARE_FACTS,
            system=template.format(skill=self._skill_body(CONSISTENCY_SKILL)),
            messages=[Message.user(text)],
            output_schema=_Conflicts.model_json_schema(),
            prompt_version=version,
        )
        calls: list[CallRecord] = []
        result = await self._call(request, calls)
        return ProposeOutcome(proposals=parse_reply(_Conflicts, result).conflicts, calls=calls)

    # --- pre-submission (§8.5) --------------------------------------------------------------

    def _case_pages(self, case_id: str) -> tuple[str, dict[tuple[str, int], str]]:
        manifest = store.load_manifest(self.cases, case_id)
        texts: dict[tuple[str, int], str] = {}
        blocks: list[str] = []
        for doc in manifest.documents:
            for ref in doc.pages:
                if ref.method == "unreadable":
                    continue
                text = store.read_page(self.cases, case_id, doc.doc_id, ref.n).text
                texts[(doc.doc_id, ref.n)] = text
                blocks.append(_page_block(doc.doc_id, doc.filename, ref.n, text))
        return "".join(blocks), texts

    @activity.defn
    @permanent
    async def measure_case(self, job: MeasureInput) -> int:
        context, _ = self._case_pages(job.case_id)
        tokens = estimate_tokens(context)
        if tokens > job.budget:
            raise fatal(
                f"the case's pages need {tokens} tokens; v1 reads at most {job.budget} per check",
                "case_too_large_for_v1",
            )
        return tokens

    @activity.defn
    @permanent
    async def check_items(self, job: ItemsInput) -> ItemsOutcome:
        checklist = self._checklist(job.checklist_skill)
        items = [i for i in checklist.items if i.id in job.item_ids]
        context, _ = self._case_pages(job.case_id)
        version, template = load_prompt("case_check_item")
        listing = "\n".join(f"- {i.id}: {i.requirement} (verify: {i.verify})" for i in items)
        request = LlmRequest(
            role=Role.CASE_CHECK_ITEM,
            system=template.format(skill=self._skill_body(job.checklist_skill)),
            messages=[
                Message.user(
                    # The same pages go with every batch: a cacheable prefix.
                    TextPart(text=f"Case pages:\n\n{context}", cache=True),
                    f"Checklist items:\n{listing}",
                )
            ],
            output_schema=_Items.model_json_schema(),
            prompt_version=version,
        )
        calls: list[CallRecord] = []
        result = await self._call(request, calls)
        return ItemsOutcome(replies=parse_reply(_Items, result).results, calls=calls)

    # --- result (§4.9) ----------------------------------------------------------------------

    @activity.defn
    @permanent
    async def write_result(self, job: FinishInput) -> CheckSummary:
        check = job.check
        manifest = store.load_manifest(self.cases, check.case_id)
        base: dict[str, Any] = {
            "check_id": check.check_id,
            "case_id": check.case_id,
            "kind": check.kind,
            "started": job.started,
            "finished": job.finished,
            "calls": job.calls,
        }
        if job.error is not None:
            result = CheckResult(
                **base, status="failed", error=job.error, coverage=build_coverage(manifest)
            )
        else:
            result = self._completed(job, manifest, base)
        store.write_result(self.cases, result)
        counts = status_counts(result.items)
        return CheckSummary(
            check_id=result.check_id,
            status=result.status,
            error=result.error,
            conflicts=len(result.conflicts),
            checked=counts["checked"],
            pending=counts["pending"],
            unable=counts["unable"],
            gaps=len(result.gaps),
            clean=is_clean(result),
        )

    def _completed(self, job: FinishInput, manifest: Any, base: dict[str, Any]) -> CheckResult:
        check = job.check
        gaps = build_gaps(manifest, job.extraction_failures)
        if check.kind == "consistency":
            categories = self._categories()
            accepted, dropped = accept_model_conflicts(job.proposals, job.facts, categories)
            names = {d.doc_id: d.filename for d in manifest.documents}
            conflicts, replaced = merge_conflicts(
                rule_baseline(job.facts, categories), accepted, job.facts, names
            )
            return CheckResult(
                **base,
                status="completed",
                error=job.model_error,
                coverage=build_coverage(manifest, len(job.facts), len(job.dropped)),
                facts=job.facts,
                conflicts=conflicts,
                gaps=gaps,
                dropped=[*job.dropped, *dropped],
                wording_replacements=replaced,
            )
        assert check.checklist_skill is not None
        checklist = self._checklist(check.checklist_skill)
        _, texts = self._case_pages(check.case_id)
        items, dropped = apply_item_rules(checklist, job.replies, texts, set(job.failed_items))
        return CheckResult(
            **base,
            status="completed",
            checklist=ChecklistRef(skill=check.checklist_skill, version=checklist.version),
            coverage=build_coverage(manifest),
            items=items,
            gaps=gaps,
            dropped=dropped,
        )

    def all(self) -> Sequence[Any]:
        return [
            self.load_check_spec,
            self.ingest_document,
            self.mark_document_failed,
            self.extract_facts,
            self.propose_conflicts,
            self.measure_case,
            self.check_items,
            self.write_result,
        ]
