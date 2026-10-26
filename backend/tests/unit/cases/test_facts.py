import pytest

from cairn.core.cases.facts import (
    PartialDate,
    Period,
    accept_model_conflicts,
    merge_conflicts,
    parse_normalised,
    rule_baseline,
    validate_facts,
    values_agree,
)
from cairn.core.cases.models import Fact, ModelConflict, RawFact
from cairn.core.cases.spec import Category


@pytest.mark.parametrize(
    ("kind", "a", "b", "agree"),
    [
        ("date", "2022-03", "2022-03-14", True),
        ("date", "2022", "2022-11-30", True),
        ("date", "2022-03", "2022-06-01", False),
        ("date", "1990-04-12", "1990-04-12", True),
        ("period", "2022-06/..", "2022-06-01/..", True),
        ("period", "2022-03/..", "2022-06/..", False),
        ("period", "2021-01/2022-01", "2021-01/..", False),
        ("period", "2021-01/2022-01", "2021-01-05/2022-01-31", True),
        ("text", "Warehouse  Supervisor", "warehouse supervisor", True),
        ("text", "Warehouse Supervisor", "Warehouse Manager", False),
        # One value containing the other's words in order is the same value with more detail.
        ("text", "Maintenance Engineer", "Maintenance Engineer, permanent full-time", True),
        ("text", "12 Example Street, Hamilton", "12 Example Street", True),
        ("text", "Jordon Example", "Jordan", False),
        ("text", "Engineer Maintenance", "Maintenance Engineer, permanent", False),
        ("text", "Engineer", "Engineering Manager", False),
        ("text", "", "Engineer", False),
    ],
)
def test_values_agree_at_the_coarser_precision(kind: str, a: str, b: str, agree: bool) -> None:
    assert values_agree(parse_normalised(kind, a), parse_normalised(kind, b)) is agree  # pyright: ignore[reportArgumentType]


def test_parse_normalised_shapes() -> None:
    assert parse_normalised("date", "2022-03") == PartialDate(2022, 3)
    assert parse_normalised("period", "2022-06-01/..") == Period(PartialDate(2022, 6, 1), None)
    assert parse_normalised("text", "  Alex   Sample ") == "alex sample"


@pytest.mark.parametrize(
    "bad", ["03/2022", "2022-13", "2022-02-30", "2022-00", "2022-01-00", "June 2022", ""]
)
def test_parse_date_rejects(bad: str) -> None:
    with pytest.raises(ValueError, match="date"):
        parse_normalised("date", bad)


def test_period_needs_a_slash() -> None:
    with pytest.raises(ValueError, match="period"):
        parse_normalised("period", "2022-06")


def test_sample_extraction_is_fully_accepted(sample_facts: list[Fact], expected: dict) -> None:  # pyright: ignore[reportMissingTypeArgument, reportUnknownParameterType]
    assert len(sample_facts) == expected["facts_accepted"]
    assert [f.fact_id for f in sample_facts] == [f"f{n}" for n in range(1, 15)]
    assert sample_facts[5].doc_id == "employer-letter"
    assert sample_facts[5].quote == "as Warehouse Supervisor since 1 June 2022"


def test_rule_baseline_on_the_sample(
    sample_facts: list[Fact],
    categories: list[Category],
    expected: dict,  # pyright: ignore[reportMissingTypeArgument, reportUnknownParameterType]
) -> None:
    assert rule_baseline(sample_facts, categories) == expected["rule_conflicts"]


def test_validate_facts_drops_with_reasons(categories: list[Category]) -> None:
    page = {1: "Start date: 03/2022\nRole: Warehouse Supervisor"}

    def raw(**kw: object) -> RawFact:
        base: dict[str, object] = {
            "category": "employment.period",
            "subject": "applicant",
            "value": "03/2022",
            "normalised": "2022-03/..",
            "page": 1,
            "quote": "Start date: 03/2022",
        }
        return RawFact.model_validate(base | kw)

    accepted, dropped = validate_facts(
        "q",
        [
            raw(),
            raw(category="identity.shoe_size"),
            raw(page=2),
            raw(quote="Start date: 04/2022"),
            raw(quote="start date: 03/2022"),
            raw(normalised="March 2022"),
        ],
        page,
        categories,
        first_id=7,
    )
    assert [f.fact_id for f in accepted] == ["f7"]
    assert [d.reason for d in dropped] == [
        "unknown_category",
        "page_not_in_unit",
        "citation_invalid",
        "citation_invalid",
        "bad_normalised",
    ]


def _fact(fact_id: str, doc: str, category: str, normalised: str, **kw: str) -> Fact:
    return Fact(
        fact_id=fact_id,
        category=category,
        subject=kw.get("subject", "applicant"),
        qualifier=kw.get("qualifier"),
        value=kw.get("value", normalised),
        normalised=normalised,
        doc_id=doc,
        page=1,
        quote="q",
    )


def test_qualifiers_are_matched_fuzzily(categories: list[Category]) -> None:
    facts = [
        _fact("f1", "a", "employment.period", "2022-03/..", qualifier="Example Freight Ltd"),
        _fact("f2", "b", "employment.period", "2022-06/..", qualifier="Exampel Freight Ltd"),
        _fact("f3", "c", "employment.period", "2019-01/..", qualifier="Example Fright Co"),
    ]
    assert rule_baseline(facts, categories) == [["f1", "f2"]]


def test_disagreement_inside_one_document_is_not_a_conflict(categories: list[Category]) -> None:
    facts = [
        _fact("f1", "a", "identity.date_of_birth", "1990-04-12"),
        _fact("f2", "a", "identity.date_of_birth", "1991-04-12"),
    ]
    assert rule_baseline(facts, categories) == []


def test_accept_model_conflicts_reasons(
    sample_facts: list[Fact], categories: list[Category]
) -> None:
    proposals = [
        ModelConflict(fact_ids=["f4", "f6"], summary="s", question="q"),  # really differ
        ModelConflict(fact_ids=["f4", "f99"], summary="s", question="q"),
        ModelConflict(fact_ids=["f4", "f5"], summary="s", question="q"),  # same document
        ModelConflict(fact_ids=["f2", "f11"], summary="s", question="q"),  # dob vs employment
        ModelConflict(fact_ids=["f6", "f11"], summary="s", question="q"),  # agree by month
        # text with the same words ("Warehouse Supervisor" twice): agree. A text value that
        # really differs stays the model's call (test_a_name_in_other_words_order_...).
        ModelConflict(fact_ids=["f5", "f7"], summary="s", question="q"),
    ]
    accepted, dropped = accept_model_conflicts(proposals, sample_facts, categories)
    assert [p.fact_ids for p in accepted] == [["f4", "f6"]]
    assert [d.reason for d in dropped] == [
        "unknown_fact",
        "single_document",
        "mixed_categories",
        "values_agree",
        "values_agree",
    ]


def test_a_name_in_other_words_order_or_fields_is_not_a_conflict(
    categories: list[Category],
) -> None:
    # A passport read as SURNAME / GIVEN NAMES gives two facts; the form gives the full name.
    facts = [
        _fact("f1", "form", "identity.name", "Priya Sample"),
        _fact("f2", "passport", "identity.name", "SAMPLE"),
        _fact("f3", "passport", "identity.name", "PRIYA"),
        _fact("f4", "offer", "identity.name", "Sample, Priya"),
        _fact("f5", "letter", "identity.name", "Priya Sampel"),
    ]
    proposals = [
        ModelConflict(fact_ids=["f1", "f2", "f3", "f4"], summary="s", question="q"),
        ModelConflict(fact_ids=["f1", "f5"], summary="s", question="q"),  # a real misspelling
    ]
    accepted, dropped = accept_model_conflicts(proposals, facts, categories)
    assert [p.fact_ids for p in accepted] == [["f1", "f5"]]
    assert [(d.reason, d.detail) for d in dropped] == [("values_agree", "f1, f2, f3, f4")]


def test_merge_conflicts_origins_and_wording(sample_facts: list[Fact]) -> None:
    names = {
        "questionnaire": "Questionnaire",
        "employer-letter": "Employer letter",
        "application-form": "Application form",
        "tenancy": "Tenancy agreement",
    }
    model = [
        ModelConflict(
            fact_ids=["f4", "f6"],
            summary="Job start differs",
            question="Which start date is right: March or June 2022?",
        ),
        ModelConflict(
            fact_ids=["f5", "f7"], summary="Role", question="Is the employer letter false?"
        ),
    ]
    conflicts, replaced = merge_conflicts(
        [["f3", "f10", "f14"], ["f4", "f6", "f11"]], model, sample_facts, names
    )
    assert replaced == 1
    assert [(c.finding_id, c.fact_ids, c.origin, c.drafted_by) for c in conflicts] == [
        ("c1", ["f3", "f10", "f14"], ["rule"], "template"),
        ("c2", ["f4", "f6", "f11"], ["rule", "model"], "model"),
        ("c3", ["f5", "f7"], ["model"], "template"),
    ]
    assert conflicts[0].question == (
        "Questionnaire (page 1) gives since 01/2021; "
        "Application form (page 1) gives from January 2021; "
        "Tenancy agreement (page 1) gives from 1 May 2021. Which is correct?"
    )
    assert conflicts[1].question == "Which start date is right: March or June 2022?"
    assert "false" not in conflicts[2].question


def test_merge_consumes_every_covered_or_duplicate_proposal(sample_facts: list[Fact]) -> None:
    def proposal(ids: list[str], question: str) -> ModelConflict:
        return ModelConflict(fact_ids=ids, summary="s", question=question)

    model = [
        proposal(["f4", "f6"], "Which start date: March or June 2022?"),
        proposal(["f4", "f11"], "Second wording for the same conflict"),
        proposal(["f6", "f4"], "Same facts again, other order"),
        proposal(["f5", "f7"], "Is the role the same in both?"),
        proposal(["f7", "f5"], "Duplicate of the role question"),
    ]
    conflicts, replaced = merge_conflicts([["f4", "f6", "f11"]], model, sample_facts, {})
    assert replaced == 0
    assert [(c.fact_ids, c.origin, c.question) for c in conflicts] == [
        (["f4", "f6", "f11"], ["rule", "model"], "Which start date: March or June 2022?"),
        (["f5", "f7"], ["model"], "Is the role the same in both?"),
    ]


def test_overlapping_addresses_from_different_documents_conflict(
    categories: list[Category],
) -> None:
    form, bank, lease = "form", "bank", "lease"
    facts = [
        _fact("f1", form, "address.period", "2020-03/..", qualifier="7 Placeholder Road"),
        _fact("f2", bank, "address.period", "2021-06-01/2021-06-30", qualifier="21 Fictional Ave"),
        # Moving month: ends 2019-01, next starts 2019-01. Touching, not overlapping.
        _fact("f3", lease, "address.period", "2018-02/2019-01", qualifier="3 Old Street"),
        _fact("f4", form, "address.period", "2019-01-15/2020-03", qualifier="9 Middle Road"),
        # Two jobs at once are normal: employment periods never conflict by overlap.
        _fact("f5", form, "employment.period", "2020-01/..", qualifier="Demo Orchards Ltd"),
        _fact("f6", bank, "employment.period", "2021-01/..", qualifier="Night Cafe Ltd"),
    ]
    assert rule_baseline(facts, categories) == [["f1", "f2"]]


def test_overlap_needs_two_documents_and_the_same_person(categories: list[Category]) -> None:
    facts = [
        _fact("f1", "form", "address.period", "2020-03/..", qualifier="7 Placeholder Road"),
        _fact("f2", "form", "address.period", "2021-06/2021-07", qualifier="21 Fictional Ave"),
        _fact(
            "f3",
            "bank",
            "address.period",
            "2021-06/2021-07",
            qualifier="21 Fictional Ave",
            subject="partner",
        ),
    ]
    assert rule_baseline(facts, categories) == []


def test_overlap_conflicts_name_each_address_in_the_template() -> None:
    facts = [
        _fact(
            "f1",
            "form",
            "address.period",
            "2020-03/..",
            qualifier="7 Placeholder Road",
            value="from March 2020",
        ),
        _fact(
            "f2",
            "bank",
            "address.period",
            "2021-06/2021-06",
            qualifier="21 Fictional Ave",
            value="June 2021",
        ),
    ]
    [conflict], _ = merge_conflicts([["f1", "f2"]], [], facts, {"form": "Form", "bank": "Bank"})
    assert conflict.question == (
        "Form (page 1) gives 7 Placeholder Road: from March 2020; "
        "Bank (page 1) gives 21 Fictional Ave: June 2021. Which is correct?"
    )


def test_fuzzy_matched_qualifiers_are_one_place_in_the_template() -> None:
    facts = [
        _fact("f1", "a", "employment.period", "2022-03/..", qualifier="Example Freight Ltd"),
        _fact("f2", "b", "employment.period", "2022-06/..", qualifier="Exampel Freight Ltd"),
    ]
    [conflict], _ = merge_conflicts([["f1", "f2"]], [], facts, {"a": "A", "b": "B"})
    assert (
        conflict.question
        == "A (page 1) gives 2022-03/..; B (page 1) gives 2022-06/... Which is correct?"
    )
