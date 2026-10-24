"""Consistency check rules: validate extracted facts, find conflicts, accept model proposals.

Design §8.3 (validation) and §8.4 (compare). The model drafts; this module decides.
"""

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date

from rapidfuzz import fuzz

from cairn.core.cases.citations import normalise_ws, quote_on_page
from cairn.core.cases.models import Conflict, Dropped, Fact, ModelConflict, Origin, RawFact
from cairn.core.cases.spec import Category, Kind, kinds_by_id
from cairn.core.cases.wording import template_question, template_summary, uses_banned_wording

QUALIFIER_MATCH = 0.90
_DATE = re.compile(r"^(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?$")
OPEN_END = ".."


@dataclass(frozen=True)
class PartialDate:
    """A date known to year, month or day precision."""

    year: int
    month: int | None = None
    day: int | None = None

    def precision(self) -> int:
        return 1 if self.month is None else 2 if self.day is None else 3

    def truncated(self, precision: int) -> tuple[int, ...]:
        return (self.year, self.month or 0, self.day or 0)[:precision]


@dataclass(frozen=True)
class Period:
    start: PartialDate
    end: PartialDate | None  # None = open (still current)


Normalised = PartialDate | Period | str


def parse_date(text: str) -> PartialDate:
    match = _DATE.match(text.strip())
    if not match:
        raise ValueError(f"not a YYYY, YYYY-MM or YYYY-MM-DD date: {text!r}")
    year, month, day = (int(g) if g else None for g in match.groups())
    assert year is not None
    try:
        date(year, 1 if month is None else month, 1 if day is None else day)
    except ValueError as exc:
        raise ValueError(f"not a real date: {text!r} ({exc})") from exc
    return PartialDate(year, month, day)


def parse_period(text: str) -> Period:
    start, sep, end = text.strip().partition("/")
    if not sep:
        raise ValueError(f"not a <start>/<end> period: {text!r}")
    return Period(parse_date(start), None if end == OPEN_END else parse_date(end))


def parse_normalised(kind: Kind, text: str) -> Normalised:
    if kind == "date":
        return parse_date(text)
    if kind == "period":
        return parse_period(text)
    return normalise_ws(text).casefold()


def dates_agree(a: PartialDate, b: PartialDate) -> bool:
    """Compare at the coarser precision: 2022-03 agrees with 2022-03-14."""
    precision = min(a.precision(), b.precision())
    return a.truncated(precision) == b.truncated(precision)


def values_agree(a: Normalised, b: Normalised) -> bool:
    if isinstance(a, PartialDate) and isinstance(b, PartialDate):
        return dates_agree(a, b)
    if isinstance(a, Period) and isinstance(b, Period):
        if not dates_agree(a.start, b.start):
            return False
        if a.end is None or b.end is None:
            return a.end is None and b.end is None
        return dates_agree(a.end, b.end)
    return a == b


# --- §8.3 validation ------------------------------------------------------------------------


def validate_facts(
    doc_id: str,
    raw_facts: Iterable[RawFact],
    pages: Mapping[int, str],
    categories: Sequence[Category],
    first_id: int,
) -> tuple[list[Fact], list[Dropped]]:
    """Accept facts whose category, page, quote and normalised value all check out.

    `pages` holds the text of the pages this extraction unit covered. Accepted facts get ids
    `f<first_id>`, `f<first_id + 1>`, … in input order.
    """
    kinds = kinds_by_id(categories)
    accepted: list[Fact] = []
    dropped: list[Dropped] = []
    for raw in raw_facts:
        where = f"{doc_id} p{raw.page} {raw.category}"
        kind = kinds.get(raw.category)
        if kind is None:
            dropped.append(Dropped(reason="unknown_category", detail=where))
            continue
        if raw.page not in pages:
            dropped.append(Dropped(reason="page_not_in_unit", detail=where))
            continue
        if not quote_on_page(raw.quote, pages[raw.page]):
            dropped.append(Dropped(reason="citation_invalid", detail=f"{where}: {raw.quote!r}"))
            continue
        try:
            parse_normalised(kind, raw.normalised)
        except ValueError as exc:
            dropped.append(Dropped(reason="bad_normalised", detail=f"{where}: {exc}"))
            continue
        accepted.append(
            Fact(fact_id=f"f{first_id + len(accepted)}", doc_id=doc_id, **raw.model_dump())
        )
    return accepted, dropped


# --- §8.4 compare ---------------------------------------------------------------------------


def _key_text(text: str | None) -> str:
    return normalise_ws(text or "").casefold()


def _groups(facts: Sequence[Fact]) -> list[list[Fact]]:
    """Group facts about the same thing: category, subject, and a qualifier that matches."""
    groups: list[tuple[tuple[str, str], str, list[Fact]]] = []
    for fact in facts:
        key = (fact.category, _key_text(fact.subject))
        qualifier = _key_text(fact.qualifier)
        for group_key, representative, members in groups:
            if group_key == key and _qualifiers_match(qualifier, representative):
                members.append(fact)
                break
        else:
            groups.append((key, qualifier, [fact]))
    return [members for _, _, members in groups]


def _qualifiers_match(a: str, b: str) -> bool:
    if not a or not b:
        return a == b
    return fuzz.token_set_ratio(a, b) / 100 >= QUALIFIER_MATCH


def _disagree_across_documents(facts: Sequence[Fact], kind: Kind) -> bool:
    for i, a in enumerate(facts):
        for b in facts[i + 1 :]:
            if a.doc_id == b.doc_id:
                continue
            if not values_agree(
                parse_normalised(kind, a.normalised), parse_normalised(kind, b.normalised)
            ):
                return True
    return False


def rule_baseline(facts: Sequence[Fact], categories: Sequence[Category]) -> list[list[str]]:
    """Fact-id sets, one per group whose values differ between documents (in fact order)."""
    kinds = kinds_by_id(categories)
    return [
        [f.fact_id for f in group]
        for group in _groups(facts)
        if _disagree_across_documents(group, kinds[group[0].category])
    ]


def accept_model_conflicts(
    proposals: Iterable[ModelConflict], facts: Sequence[Fact], categories: Sequence[Category]
) -> tuple[list[ModelConflict], list[Dropped]]:
    by_id = {f.fact_id: f for f in facts}
    kinds = kinds_by_id(categories)
    accepted: list[ModelConflict] = []
    dropped: list[Dropped] = []
    for proposal in proposals:
        ids = ", ".join(proposal.fact_ids)
        members = [by_id[i] for i in proposal.fact_ids if i in by_id]
        if len(members) != len(proposal.fact_ids):
            dropped.append(Dropped(reason="unknown_fact", detail=ids))
        elif len({f.doc_id for f in members}) < 2:
            dropped.append(Dropped(reason="single_document", detail=ids))
        elif len({f.category for f in members}) != 1:
            dropped.append(Dropped(reason="mixed_categories", detail=ids))
        elif kinds[members[0].category] != "text" and not _disagree_across_documents(
            members, kinds[members[0].category]
        ):
            dropped.append(Dropped(reason="values_agree", detail=ids))
        else:
            accepted.append(proposal)
    return accepted, dropped


def merge_conflicts(
    rule_sets: Sequence[Sequence[str]],
    model: Sequence[ModelConflict],
    facts: Sequence[Fact],
    doc_names: Mapping[str, str],
) -> tuple[list[Conflict], int]:
    """Union of rule and model conflicts; returns the conflicts and how many model wordings
    the wording guard replaced with the template.

    Model proposals with the same fact-id set count once. Every model proposal whose facts are a
    subset of a rule conflict's facts merges into it; the first lends it its wording.
    """
    by_id = {f.fact_id: f for f in facts}
    # One proposal per fact-id set; the first one keeps its wording.
    unique: dict[frozenset[str], ModelConflict] = {}
    for proposal in model:
        unique.setdefault(frozenset(proposal.fact_ids), proposal)
    unmerged = list(unique.values())
    drafts: list[tuple[list[str], list[Origin], ModelConflict | None]] = []
    for rule_ids in rule_sets:
        covered = [m for m in unmerged if set(m.fact_ids) <= set(rule_ids)]
        unmerged = [m for m in unmerged if m not in covered]
        if covered:
            drafts.append((list(rule_ids), ["rule", "model"], covered[0]))
        else:
            drafts.append((list(rule_ids), ["rule"], None))
    drafts.extend((list(m.fact_ids), ["model"], m) for m in unmerged)

    conflicts: list[Conflict] = []
    replaced = 0
    for n, (ids, origin, proposal) in enumerate(drafts, start=1):
        members = [by_id[i] for i in ids]
        statements = [(doc_names.get(f.doc_id, f.doc_id), f.page, f.value) for f in members]
        usable = proposal
        if proposal and (
            uses_banned_wording(proposal.question) or uses_banned_wording(proposal.summary)
        ):
            usable, replaced = None, replaced + 1
        conflicts.append(
            Conflict(
                finding_id=f"c{n}",
                fact_ids=ids,
                origin=origin,
                summary=usable.summary
                if usable
                else template_summary(members[0].category, statements),
                question=usable.question if usable else template_question(statements),
                drafted_by="model" if usable else "template",
            )
        )
    return conflicts, replaced
