"""Sniffing, quotes, wording, spec parsing and pre-submission item rules."""

from pathlib import Path

import pytest

from cairn.core.cases.citations import quote_on_page
from cairn.core.cases.items import apply_item_rules, status_counts
from cairn.core.cases.models import Citation, ItemReply
from cairn.core.cases.sniff import sniff
from cairn.core.cases.spec import (
    SpecInvalid,
    list_checklists,
    load_checklist,
    parse_categories,
    parse_checklist,
)
from cairn.core.cases.wording import template_question, uses_banned_wording
from cairn.errors import Unsupported
from tests.unit.cases.conftest import SAMPLE, SKILLS

# --- sniff ----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("questionnaire.pdf", ("application/pdf", "pdf")),
        ("passport-scan.png", ("image/png", "png")),
        ("unreadable-photo.jpg", ("image/jpeg", "jpg")),
    ],
)
def test_sniff_sample_files(name: str, expected: tuple[str, str]) -> None:
    assert sniff(name, (SAMPLE / name).read_bytes()) == expected


def test_sniff_trusts_bytes_not_names() -> None:
    assert sniff("letter.txt", (SAMPLE / "tenancy.pdf").read_bytes()) == ("application/pdf", "pdf")
    assert sniff("notes.md", "# Notes\nčešt".encode()) == ("text/markdown", "md")


@pytest.mark.parametrize(
    ("name", "data"),
    [
        ("evil.exe", b"MZ\x90\x00"),
        ("notes.txt", b"\xff\xfe\x00bad"),
        ("latin1.txt", b"caf\xe9 au lait"),
        ("page.html", b"<html></html>"),
    ],
)
def test_sniff_rejects(name: str, data: bytes) -> None:
    with pytest.raises(Unsupported) as info:
        sniff(name, data)
    assert info.value.code == "unsupported_type"


# --- quotes and wording ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("quote", "page", "found"),
    [
        ("since 1 June 2022", "employed\nsince 1 June 2022.", True),
        ("Warehouse Supervisor since 1 June", "as Warehouse Supervisor\n  since 1 June", True),
        ("since 1 june 2022", "since 1 June 2022", False),
        ("", "anything", False),
        ("   ", "anything", False),
        ("1 July", "1 June", False),
    ],
)
def test_quote_on_page(quote: str, page: str, found: bool) -> None:
    assert quote_on_page(quote, page) is found


@pytest.mark.parametrize(
    ("text", "banned"),
    [
        ("Is the letter false?", True),
        ("This may be FRAUDULENT", True),
        ("Which date is incorrect?", True),
        ("Which is correct?", False),
        ("The employer's address", False),
    ],
)
def test_wording_guard(text: str, banned: bool) -> None:
    assert uses_banned_wording(text) is banned


def test_template_question() -> None:
    assert template_question([("Questionnaire", 2, "03/2022"), ("Employer letter", 1, "June")]) == (
        "Questionnaire (page 2) gives 03/2022; Employer letter (page 1) gives June. "
        "Which is correct?"
    )


# --- spec -----------------------------------------------------------------------------------


def test_fixture_categories() -> None:
    text = (SKILLS / "case-consistency-check/references/fact-categories.md").read_text()
    assert [(c.id, c.kind) for c in parse_categories(text)] == [
        ("identity.name", "text"),
        ("identity.date_of_birth", "date"),
        ("identity.passport_number", "text"),
        ("identity.nationality", "text"),
        ("address.period", "period"),
        ("employment.period", "period"),
        ("employment.role", "text"),
        ("family.member", "text"),
        ("travel.period", "period"),
        ("prior_application", "text"),
    ]


def test_fixture_checklist() -> None:
    checklist = load_checklist(SKILLS / "presubmission-aewv")
    assert (checklist.visa, checklist.version, checklist.owner) == (
        "aewv",
        "0.1-sample",
        "senior adviser",
    )
    assert [i.id for i in checklist.items] == [
        "passport-present",
        "names-match",
        "job-offer-present",
        "forms-signed-dated",
        "translations-present",
        "referenced-attachments-exist",
        "police-certificates",
        "client-promised-documents",
    ]


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("items: [", "not valid YAML"),
        ("- a\n- b", "checklist: Input should be a valid dictionary"),
        ("visa: x\nversion: 1\nowner: o\nitems: []", "items: Tuple should have at least 1 item"),
        (
            "version: 1\nowner: o\nitems: [{id: a, requirement: r, verify: v}]",
            "visa: Field required",
        ),
        (
            "visa: x\nversion: 1\nowner: o\nitems: [{id: Bad_Id, requirement: r, verify: v}]",
            "items.0.id: String should match pattern",
        ),
        (
            "visa: x\nversion: 1\nowner: o\nitems: [{id: a, verify: v}]",
            "items.0.requirement: Field required",
        ),
        (
            "visa: x\nversion: 1\nowner: '  '\nitems: [{id: a, requirement: r, verify: v}]",
            "owner: String should have at least 1 character",
        ),
        (
            "visa: x\nversion: 1\nowner: o\nitems: "
            "[{id: a, requirement: r, verify: v}, {id: a, requirement: r, verify: v}]",
            "duplicate checklist item ids: a",
        ),
    ],
)
def test_invalid_checklists(text: str, message: str) -> None:
    with pytest.raises(SpecInvalid, match=message) as info:
        parse_checklist(text)
    assert info.value.code == "spec_invalid"


def test_invalid_categories() -> None:
    with pytest.raises(SpecInvalid, match="lists no categories"):
        parse_categories("# nothing here")
    dup = "| `a.b` | person | date | x |\n| `a.b` | person | text | y |"
    with pytest.raises(SpecInvalid, match=r"duplicate fact categories: a\.b"):
        parse_categories(dup)


def test_list_checklists_reports_broken_ones(tmp_path: Path) -> None:
    good = tmp_path / "presubmission-good" / "references"
    good.mkdir(parents=True)
    (good / "checklist.yaml").write_text(
        "visa: g\nversion: 1\nowner: o\nitems: [{id: a, requirement: r, verify: v}]"
    )
    (tmp_path / "presubmission-broken").mkdir()
    (tmp_path / "case-consistency-check").mkdir()
    infos = list_checklists(tmp_path)
    assert [(i.skill, i.checklist is not None, i.error is not None) for i in infos] == [
        ("presubmission-broken", False, True),
        ("presubmission-good", True, False),
    ]


# --- items ----------------------------------------------------------------------------------


def test_item_rules_every_item_gets_one_honest_status() -> None:
    checklist = load_checklist(SKILLS / "presubmission-aewv")
    pages = {("cover", 1): "Appendix 7 police certificate.", ("form", 2): "Applicant signature"}
    good = Citation(doc_id="cover", page=1, quote="Appendix 7 police certificate.")
    bad = Citation(doc_id="cover", page=1, quote="Appendix 8")
    replies = [
        ItemReply(item_id="passport-present", status="checked", finding="ok", citations=[bad]),
        ItemReply(item_id="names-match", status="checked", finding="ok", citations=[]),
        ItemReply(
            item_id="referenced-attachments-exist",
            status="pending",
            finding="Appendix 7 is cited but not in the case",
            citations=[good],
        ),
        ItemReply(item_id="referenced-attachments-exist", status="checked", finding="dup"),
        ItemReply(item_id="not-on-the-list", status="checked", finding="x"),
        ItemReply(
            item_id="forms-signed-dated",
            status="checked",
            finding="signed",
            citations=[Citation(doc_id="form", page=2, quote="Applicant signature")],
        ),
    ]
    items, dropped = apply_item_rules(
        checklist, replies, pages, failed_items={"translations-present"}
    )
    assert [(i.finding_id, i.item_id, i.status, i.downgraded) for i in items] == [
        ("i1", "passport-present", "pending", "no_valid_citation"),
        ("i2", "names-match", "pending", "no_valid_citation"),
        ("i3", "job-offer-present", "unable", "missing"),
        ("i4", "forms-signed-dated", "checked", None),
        ("i5", "translations-present", "unable", "call_failed"),
        ("i6", "referenced-attachments-exist", "pending", None),
        ("i7", "police-certificates", "unable", "missing"),
        ("i8", "client-promised-documents", "unable", "missing"),
    ]
    assert items[5].citations == [good]
    assert [d.reason for d in dropped] == ["duplicate_item", "unknown_item", "citation_invalid"]
    assert status_counts(items) == {"checked": 1, "pending": 3, "unable": 4}
