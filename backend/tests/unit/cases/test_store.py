import hashlib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from cairn.core.cases import store
from cairn.core.cases.coverage import build_coverage, build_gaps, is_clean
from cairn.core.cases.models import (
    CheckResult,
    Conflict,
    Coverage,
    Gap,
    ItemResult,
    Page,
    PageRef,
)
from cairn.errors import CairnError
from tests.unit.cases.conftest import SAMPLE

NOW = datetime(2026, 10, 24, 3, 0, tzinfo=UTC)
LIMITS = store.CaseLimits(max_documents=3, max_file_bytes=100_000)


@pytest.fixture
def case(cases_dir: Path) -> Path:
    store.create_case(cases_dir, "C1", "AEWV sample 1", "synthetic", NOW)
    return cases_dir


def _upload(cases_dir: Path, doc_id: str, name: str) -> None:
    data = (SAMPLE / name).read_bytes()
    store.add_document(cases_dir, "C1", doc_id, name, data, NOW, LIMITS)


def test_create_and_load_manifest(case: Path) -> None:
    manifest = store.load_manifest(case, "C1")
    assert (manifest.case_id, manifest.label, manifest.data_class, manifest.documents) == (
        "C1",
        "AEWV sample 1",
        "synthetic",
        [],
    )
    with pytest.raises(CairnError) as info:
        store.create_case(case, "C1", "again", "synthetic", NOW)
    assert info.value.code == "case_exists"


def test_unknown_case_is_not_found(cases_dir: Path) -> None:
    with pytest.raises(CairnError) as info:
        store.load_manifest(cases_dir, "nope")
    assert (info.value.code, info.value.status) == ("case_not_found", 404)


def test_add_document_stores_original_bytes(case: Path) -> None:
    _upload(case, "D1", "employer-letter.pdf")
    data = (SAMPLE / "employer-letter.pdf").read_bytes()
    doc = store.load_manifest(case, "C1").documents[0]
    assert (doc.doc_id, doc.filename, doc.media_type, doc.bytes, doc.status) == (
        "D1",
        "employer-letter.pdf",
        "application/pdf",
        len(data),
        "pending",
    )
    assert doc.sha256 == hashlib.sha256(data).hexdigest()
    assert store.original_path(case, "C1", "D1").read_bytes() == data
    assert store.original_path(case, "C1", "D1").name == "D1.pdf"


def test_repeated_upload_is_idempotent(case: Path) -> None:
    _upload(case, "D1", "tenancy.pdf")
    _upload(case, "D1", "tenancy.pdf")
    assert [d.doc_id for d in store.load_manifest(case, "C1").documents] == ["D1"]
    with pytest.raises(CairnError) as info:
        _upload(case, "D1", "cover-letter.pdf")
    assert info.value.code == "document_exists"


@pytest.mark.parametrize("bad", ["../C1", "a/b", "", "x" * 65, "C1.json"])
def test_ids_that_could_escape_the_case_are_rejected(case: Path, bad: str) -> None:
    for call in (
        lambda: store.load_manifest(case, bad),
        lambda: store.read_page(case, "C1", bad, 1),
        lambda: store.read_result(case, "C1", bad),
    ):
        with pytest.raises(CairnError) as info:
            call()
        assert (info.value.code, info.value.status) == ("invalid_id", 422)


def test_upload_limits(case: Path) -> None:
    big = b"%PDF-" + b"0" * 100_000
    with pytest.raises(CairnError) as info:
        store.add_document(case, "C1", "D0", "big.pdf", big, NOW, LIMITS)
    assert (info.value.code, info.value.status) == ("case_too_large", 413)
    for n, name in enumerate(["tenancy.pdf", "cover-letter.pdf", "employer-letter.pdf"]):
        _upload(case, f"D{n}", name)
    with pytest.raises(CairnError) as info:
        _upload(case, "D9", "questionnaire.pdf")
    assert info.value.code == "case_too_large"
    assert len(store.load_manifest(case, "C1").documents) == 3


def test_pages_round_trip_and_ingest_status(case: Path) -> None:
    _upload(case, "D1", "passport-scan.png")
    page = Page(
        doc_id="D1",
        page=1,
        method="transcribed",
        source_sha256="abc",
        model="anthropic/claude-sonnet-5.5",
        text="Surname: SAMPLE\n\nGiven names: ALEX\n",
    )
    store.write_pages(case, "C1", [page])
    assert store.read_page(case, "C1", "D1", 1) == page
    doc = store.set_document_ingest(
        case, "C1", "D1", "ingested", [PageRef(n=1, method="transcribed")]
    )
    assert store.load_manifest(case, "C1").documents[0] == doc
    with pytest.raises(CairnError) as info:
        store.read_page(case, "C1", "D1", 2)
    assert info.value.code == "page_not_found"


def _result(**kw: object) -> CheckResult:
    base: dict[str, object] = {
        "check_id": "K1",
        "case_id": "C1",
        "kind": "presubmission",
        "started": NOW,
        "finished": NOW,
        "status": "completed",
        "coverage": Coverage(
            documents=1, documents_failed=0, pages=1, pages_transcribed=0, pages_unreadable=0
        ),
        "conflicts": [],
        "items": [
            ItemResult(finding_id="i1", item_id="a", status="checked", finding="ok"),
            ItemResult(finding_id="i2", item_id="b", status="pending", finding="missing x"),
            ItemResult(finding_id="i3", item_id="c", status="unable", finding="unclear"),
        ],
        "gaps": [Gap(finding_id="g1", doc_id="D2", kind="unreadable", pages=[1], reason="blur")],
    }
    return CheckResult.model_validate(base | kw)


def test_results_are_immutable(case: Path) -> None:
    store.write_result(case, _result())
    assert store.read_result(case, "C1", "K1") == _result()
    store.write_result(case, _result())  # a retried activity writes the same result: no-op
    with pytest.raises(CairnError) as info:
        store.write_result(case, _result(status="failed"))
    assert info.value.code == "result_exists"
    assert store.read_result(case, "C1", "K1").status == "completed"


def test_review_and_signoff_rules(case: Path) -> None:
    result = _result()
    store.write_result(case, result)

    def review(finding: str, action: str, note: str | None = None) -> None:
        store.record_review(case, result, finding, action, note, "A. Adviser", NOW)  # pyright: ignore[reportArgumentType]

    with pytest.raises(CairnError) as info:
        review("i9", "confirmed")
    assert info.value.code == "unknown_finding"
    with pytest.raises(CairnError) as info:
        review("i2", "dismissed", "  ")
    assert (info.value.code, info.value.status) == ("note_required", 422)

    review("i2", "confirmed")
    review("g1", "resolved")
    with pytest.raises(CairnError) as info:
        store.sign_off(case, result, "A. Adviser", NOW)
    assert (info.value.code, info.value.message) == (
        "signoff_blocked",
        "settle these findings first: i3",
    )

    review("i3", "dismissed", "Adviser will check the original")
    review("g1", "reopened")
    assert store.signoff_blockers(result, store.read_audit(case, "C1")) == ["g1"]
    review("g1", "confirmed")
    entry = store.sign_off(case, result, "A. Adviser", NOW)
    assert (entry.action, entry.finding_id, entry.adviser) == ("signed_off", None, "A. Adviser")
    audit = store.read_audit(case, "C1")
    assert [(e.finding_id, e.action) for e in audit] == [
        ("i2", "confirmed"),
        ("g1", "resolved"),
        ("i3", "dismissed"),
        ("g1", "reopened"),
        ("g1", "confirmed"),
        (None, "signed_off"),
    ]
    assert store.review_states(audit, "K1") == {
        "i2": "confirmed",
        "g1": "confirmed",
        "i3": "dismissed",
    }


def test_gaps_coverage_and_clean(case: Path) -> None:
    _upload(case, "D1", "questionnaire.pdf")
    _upload(case, "D2", "unreadable-photo.jpg")
    _upload(case, "D3", "tenancy.pdf")
    store.set_document_ingest(
        case, "C1", "D1", "ingested", [PageRef(n=1, method="text"), PageRef(n=2, method="text")]
    )
    store.set_document_ingest(case, "C1", "D2", "ingested", [PageRef(n=1, method="unreadable")])
    store.set_document_ingest(case, "C1", "D3", "failed", [], error="vendor timed out")
    manifest = store.load_manifest(case, "C1")
    assert build_gaps(manifest) == [
        Gap(
            finding_id="g1",
            doc_id="D2",
            kind="unreadable",
            pages=[1],
            reason="unreadable-photo.jpg: 1 page(s) could not be read",
        ),
        Gap(finding_id="g2", doc_id="D3", kind="failed", reason="vendor timed out"),
    ]
    assert build_coverage(manifest, 5, 1) == Coverage(
        documents=3,
        documents_failed=1,
        pages=3,
        pages_transcribed=0,
        pages_unreadable=1,
        facts_accepted=5,
        facts_dropped=1,
    )
    assert not is_clean(_result())
    checked = [ItemResult(finding_id="i1", item_id="a", status="checked", finding="ok")]
    assert is_clean(_result(items=checked, gaps=[]))
    assert not is_clean(_result(items=checked))  # only the unreadable page is open
    conflict = Conflict(
        finding_id="c1",
        fact_ids=["f1", "f2"],
        origin=["rule"],
        summary="s",
        question="q",
        drafted_by="template",
    )
    assert not is_clean(_result(kind="consistency", items=[], gaps=[], conflicts=[conflict]))
    assert is_clean(_result(kind="consistency", items=[], gaps=[]))
