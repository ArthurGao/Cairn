"""INZ letter rules (design §8.8): passages, deadline, coverage, evidence, drafts, working days."""

from datetime import date

import pytest

from cairn.core.cases.letters import (
    apply_evidence_rules,
    apply_letter_rules,
    client_email,
    dates_in,
    reply_outline,
    split_passages,
    working_days_until,
)
from cairn.core.cases.models import (
    Citation,
    Concern,
    Deadline,
    EvidenceReply,
    LetterConcern,
    LetterReading,
    RawConcern,
    RawDeadline,
)
from tests.fixtures.cases.make_cases import LETTERS

LETTER = {n: "\r\n".join(lines) for n, lines in enumerate(LETTERS["ppi-aewv.pdf"], start=1)}
PASSAGES = split_passages(sorted(LETTER.items()))


# --- passages -------------------------------------------------------------------------------


def test_split_passages_numbers_lines_and_joins_wrapped_sentences() -> None:
    assert [(p.passage_id, p.page, p.text) for p in PASSAGES] == [
        ("P1", 1, "Immigration New Zealand (sample letter - not a real document)"),
        ("P2", 1, "Our reference: SAMPLE-0001"),
        ("P3", 1, "24 October 2026"),
        ("P4", 1, "Dear Alex Sample"),
        ("P5", 1, "Re: Accredited Employer Work Visa application"),
        ("P6", 1, "We are writing about your application for an Accredited Employer Work Visa."),
        ("P7", 1, "Before we decide it, you have the chance to comment on the following concerns."),
        (
            "P8",
            1,
            "1. Your questionnaire gives your start date with Example Freight Ltd as 03/2022.",
        ),
        ("P9", 1, "Your employer's letter states you have been employed since 1 June 2022."),
        ("P10", 1, "2. Your application lists a police certificate, but none has been received."),
        (
            "P11",
            1,
            "3. Your application form states you have lived at 12 Example Street since "
            "January 2021.",
        ),
        ("P12", 2, "Please provide evidence of when you began living at this address."),
        (
            "P13",
            2,
            "If you do not respond by 7 November 2026, we will decide your application on the "
            "information we hold.",
        ),
        ("P14", 2, "Yours sincerely"),
        ("P15", 2, "A. Officer, Immigration Officer"),
    ]


def test_split_passages_starts_a_list_item_and_skips_blank_lines() -> None:
    first = "(a) a first point long enough that it would otherwise read as a wrapped line"
    passages = split_passages([(1, f"Concerns\n\n{first}\n(b) second point\n- third")])
    assert [p.text for p in passages] == ["Concerns", first, "(b) second point", "- third"]
    # A blank line always ends a passage, even mid-sentence.
    assert [p.text for p in split_passages([(1, "Our ref\n\nsee below")])] == [
        "Our ref",
        "see below",
    ]


# --- dates ----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("respond by 7 November 2026, or", [date(2026, 11, 7)]),
        ("by 7 Nov 2026", [date(2026, 11, 7)]),
        ("by 07/11/2026 at the latest", [date(2026, 11, 7)]),
        ("by 2026-11-07.", [date(2026, 11, 7)]),
        ("between 1 June 2022 and 3 March 2023", [date(2022, 6, 1), date(2023, 3, 3)]),
        ("31/02/2026 is not a date; 03/2022 has no day", []),
    ],
)
def test_dates_in(text: str, expected: list[date]) -> None:
    assert dates_in(text) == expected


# --- reading the letter ---------------------------------------------------------------------

DEADLINE = RawDeadline(date="2026-11-07", quote="If you do not respond by 7 November 2026", page=2)


def _reading(**overrides: object) -> LetterReading:
    fields: dict[str, object] = {
        "deadline": DEADLINE,
        "concerns": [
            RawConcern(
                summary="Start date with Example Freight Ltd differs between documents",
                passages=["P8", "P9"],
                quote="start date with Example Freight Ltd as 03/2022",
                page=1,
            ),
            RawConcern(
                summary="Police certificate not received",
                passages=["P10"],
                quote="none has been received",
                page=1,
            ),
        ],
        "context_passages": [f"P{n}" for n in (1, 2, 3, 4, 5, 6, 7, 11, 12, 13, 14, 15)],
    }
    fields.update(overrides)
    return LetterReading.model_validate(fields)


def test_letter_rules_accept_concerns_and_verify_the_deadline() -> None:
    read = apply_letter_rules(_reading(), PASSAGES, LETTER)
    assert read.deadline == Deadline(
        status="verified",
        due=date(2026, 11, 7),
        quote="If you do not respond by 7 November 2026",
        page=2,
    )
    assert [(c.finding_id, c.passages) for c in read.concerns] == [
        ("q1", ["P8", "P9"]),
        ("q2", ["P10"]),
    ]
    assert read.unaccounted == []
    assert read.dropped == []
    assert read.replaced == 0


def test_every_passage_left_out_becomes_an_unaccounted_finding() -> None:
    read = apply_letter_rules(
        _reading(context_passages=["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P13", "P14"]),
        PASSAGES,
        LETTER,
    )
    assert [(u.finding_id, u.passage_id, u.page) for u in read.unaccounted] == [
        ("u1", "P11", 1),
        ("u2", "P12", 2),
        ("u3", "P15", 2),
    ]
    assert read.unaccounted[2].text == "A. Officer, Immigration Officer"


def test_a_concern_with_a_quote_not_on_its_page_is_dropped_and_its_passages_reopen() -> None:
    bad = RawConcern(summary="Police certificate", passages=["P10"], quote="no PCC", page=1)
    unknown = RawConcern(summary="Ghost", passages=["P99"], quote="Dear Alex Sample", page=1)
    reading = _reading()
    read = apply_letter_rules(
        reading.model_copy(update={"concerns": [reading.concerns[0], bad, unknown]}),
        PASSAGES,
        LETTER,
    )
    assert [c.finding_id for c in read.concerns] == ["q1"]
    assert [u.passage_id for u in read.unaccounted] == ["P10"]
    assert [d.reason for d in read.dropped] == ["citation_invalid", "unknown_passage"]


def test_unknown_context_passages_are_dropped() -> None:
    reading = _reading()
    read = apply_letter_rules(
        reading.model_copy(update={"context_passages": [*reading.context_passages, "P40"]}),
        PASSAGES,
        LETTER,
    )
    assert [(d.reason, d.detail) for d in read.dropped] == [("unknown_passage", "context: P40")]


@pytest.mark.parametrize(
    ("deadline", "expected"),
    [
        (None, Deadline(status="missing")),
        (
            DEADLINE.model_copy(update={"date": "2026-11-08"}),
            Deadline(status="unverified", due=date(2026, 11, 8), quote=DEADLINE.quote, page=2),
        ),
        (
            DEADLINE.model_copy(update={"page": 1}),
            Deadline(status="unverified", due=date(2026, 11, 7), quote=DEADLINE.quote, page=1),
        ),
        (
            DEADLINE.model_copy(update={"date": "within ten working days"}),
            Deadline(status="unverified", quote=DEADLINE.quote, page=2),
        ),
    ],
)
def test_deadline_is_verified_only_when_the_quote_carries_the_same_date(
    deadline: RawDeadline | None, expected: Deadline
) -> None:
    assert apply_letter_rules(_reading(deadline=deadline), PASSAGES, LETTER).deadline == expected


def test_banned_wording_in_a_concern_summary_is_replaced() -> None:
    reading = _reading()
    first = reading.concerns[0].model_copy(update={"summary": "The start date is false"})
    read = apply_letter_rules(
        reading.model_copy(update={"concerns": [first, reading.concerns[1]]}), PASSAGES, LETTER
    )
    assert read.concerns[0].summary == "INZ raises a concern in P8, P9"
    assert read.replaced == 1


# --- evidence -------------------------------------------------------------------------------

CASE_PAGES = {
    ("questionnaire", 2): "Employer: Example Freight Ltd\nStart date: 03/2022",
    ("employer-letter", 1): "since 1 June 2022. This is a permanent full-time position.",
}
CONCERNS = [
    LetterConcern(finding_id="q1", summary="Start date", passages=["P8"], page=1, quote="03/2022"),
    LetterConcern(finding_id="q2", summary="Police", passages=["P10"], page=1, quote="none"),
    LetterConcern(finding_id="q3", summary="Address", passages=["P11"], page=1, quote="2021"),
]


def test_evidence_rules_give_every_concern_one_honest_status() -> None:
    replies = [
        EvidenceReply(
            concern_id="q1",
            status="partial",
            finding="The two documents give different start dates",
            citations=[
                Citation(doc_id="questionnaire", page=2, quote="Start date: 03/2022"),
                Citation(doc_id="employer-letter", page=1, quote="since 1 April 2022"),
            ],
            client_request="Payslips showing your first pay date",
            conflict_ids=["c1", "c9"],
        ),
        EvidenceReply(
            concern_id="q2",
            status="supported",
            finding="A certificate is listed",
            citations=[Citation(doc_id="cover-letter", page=1, quote="police certificate")],
        ),
        EvidenceReply(concern_id="q2", status="no_evidence", finding="duplicate"),
        EvidenceReply(concern_id="q7", status="no_evidence", finding="unknown"),
    ]
    concerns, dropped, replaced = apply_evidence_rules(
        CONCERNS, replies, CASE_PAGES, failed=set(), conflict_ids={"c1", "c2"}
    )
    assert [(c.finding_id, c.status, c.downgraded) for c in concerns] == [
        ("q1", "partial", None),
        ("q2", "no_evidence", "no_valid_citation"),
        ("q3", "unable", "missing"),
    ]
    assert concerns[0].citations == [
        Citation(doc_id="questionnaire", page=2, quote="Start date: 03/2022")
    ]
    assert concerns[0].conflict_ids == ["c1"]
    assert concerns[2].finding == "not evaluated"
    assert [d.reason for d in dropped] == [
        "duplicate_concern",
        "unknown_concern",
        "citation_invalid",
        "unknown_conflict",
        "citation_invalid",
    ]
    assert replaced == 0


def test_evidence_rules_mark_failed_batches_and_guard_wording() -> None:
    replies = [
        EvidenceReply(
            concern_id="q1",
            status="no_evidence",
            finding="The client's answer looks wrong",
            client_request="Explain why the questionnaire is incorrect",
        )
    ]
    concerns, _, replaced = apply_evidence_rules(
        CONCERNS, replies, CASE_PAGES, failed={"q2"}, conflict_ids=set()
    )
    assert concerns[0].finding == "No supporting evidence was found in the case"
    assert concerns[0].client_request is None
    assert (concerns[1].status, concerns[1].downgraded) == ("unable", "call_failed")
    assert replaced == 2


# --- drafts ---------------------------------------------------------------------------------


def _concern(n: int, **fields: object) -> Concern:
    base = CONCERNS[n - 1].model_dump()
    base.update({"status": "no_evidence", "finding": "Nothing found"})
    base.update(fields)
    return Concern.model_validate(base)


def test_client_email_lists_only_concerns_with_a_request() -> None:
    concerns = [
        _concern(1, client_request="Payslips showing your first pay date"),
        _concern(2, client_request="Your police certificate"),
        _concern(3),
    ]
    deadline = Deadline(status="verified", due=date(2026, 11, 7))
    assert client_email(concerns, deadline) == (
        "Hi,\n\n"
        "Immigration New Zealand has asked about some points in your application. "
        "To help us reply, please send us:\n\n"
        "1. Payslips showing your first pay date (about: Start date)\n"
        "2. Your police certificate (about: Police)\n\n"
        "INZ needs our reply by 7 November 2026, so please send these as soon as you can.\n"
    )
    assert client_email([_concern(3)], deadline) == ""


def test_reply_outline_has_one_heading_per_concern_with_its_sources() -> None:
    concerns = [
        _concern(
            1,
            status="partial",
            citations=[Citation(doc_id="questionnaire", page=2, quote="Start date: 03/2022")],
            conflict_ids=["c1"],
        ),
        _concern(2),
    ]
    outline = reply_outline(
        "ppi-aewv.pdf",
        concerns,
        {"questionnaire": "questionnaire.pdf"},
        {"c1": "employment.period differs across documents"},
    )
    assert outline == (
        "Reply to INZ letter ppi-aewv.pdf\n\n"
        "1. Start date\n"
        '   INZ (page 1): "03/2022"\n'
        "   Evidence in the case: partly supports a reply\n"
        '   - questionnaire.pdf, page 2: "Start date: 03/2022"\n'
        "   Related conflict c1: employment.period differs across documents\n"
        "   [Adviser's response]\n\n"
        "2. Police\n"
        '   INZ (page 1): "none"\n'
        "   Evidence in the case: none found\n"
        "   [Adviser's response]\n"
    )


# --- working days ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("today", "expected"),
    [
        (date(2026, 10, 26), 9),  # Mon 26 Oct -> Sat 7 Nov: 27-30 Oct, 2-6 Nov
        (date(2026, 11, 6), 0),  # Friday before a Saturday deadline
        (date(2026, 11, 7), 0),
        (date(2026, 11, 10), -2),  # Tue: Mon 9 and Tue 10 have passed
    ],
)
def test_working_days_until(today: date, expected: int) -> None:
    assert working_days_until(date(2026, 11, 7), today) == expected
