"""INZ letter rules (design §8.8): code decides what the model's reading of a letter may claim.

Every passage of the letter is accounted for (a concern or context), every concern gets exactly
one evidence status, a deadline counts as verified only when its quote carries the same date,
and the client email and reply outline are assembled from validated results, not drafted.
"""

import re
from collections.abc import Collection, Iterable, Mapping, Sequence
from datetime import date, timedelta

from cairn.core.cases.citations import PageTexts, first_replies, quote_on_page, valid_citations
from cairn.core.cases.models import (
    Citation,
    Concern,
    Deadline,
    Downgrade,
    Dropped,
    EvidenceReply,
    EvidenceStatus,
    LetterConcern,
    LetterRead,
    LetterReading,
    Manifest,
    Passage,
    RawDeadline,
    Unaccounted,
)
from cairn.core.cases.wording import uses_banned_wording
from cairn.errors import Invalid

_END = (".", "?", "!", ":", ";")
_LIST_ITEM = re.compile(r"^(\d{1,2}[.)]|\([a-z0-9]{1,4}\)|[-•*])\s")
WRAP_CHARS = 70  # a line this long that ends mid-sentence was wrapped, not a heading

_MONTHS = {
    name: n
    for n, names in enumerate(
        (
            ("january", "jan"),
            ("february", "feb"),
            ("march", "mar"),
            ("april", "apr"),
            ("may",),
            ("june", "jun"),
            ("july", "jul"),
            ("august", "aug"),
            ("september", "sep", "sept"),
            ("october", "oct"),
            ("november", "nov"),
            ("december", "dec"),
        ),
        start=1,
    )
    for name in names
}
_DATE = re.compile(
    r"\b(?:(?P<d>\d{1,2})\s+(?P<month>[A-Za-z]{3,9})\.?\s+(?P<y>\d{4})"
    r"|(?P<d2>\d{1,2})/(?P<m2>\d{1,2})/(?P<y2>\d{4})"
    r"|(?P<y3>\d{4})-(?P<m3>\d{2})-(?P<d3>\d{2}))\b"
)

EVIDENCE_TEMPLATE: dict[EvidenceStatus, str] = {
    "supported": "Evidence in the case supports a reply",
    "partial": "Evidence in the case partly supports a reply",
    "no_evidence": "No supporting evidence was found in the case",
    "unable": "Could not be judged",
}
_OUTLINE_LABEL: dict[EvidenceStatus, str] = {
    "supported": "supports a reply",
    "partial": "partly supports a reply",
    "no_evidence": "none found",
    "unable": "could not be judged",
}


def split_passages(pages: Iterable[tuple[int, str]]) -> list[Passage]:
    """Number the letter's text: one passage per line, a wrapped sentence joined to its start.

    A line continues the passage before it when that passage does not end a sentence and the
    line either starts in lower case or follows a line long enough to have been wrapped. A list
    item (`1.`, `(a)`, `-`) always starts a passage. Passages never span pages.
    """
    passages: list[Passage] = []
    for page, text in pages:
        groups: list[list[str]] = []
        last = ""
        for raw in text.splitlines():
            line = raw.strip()
            if not line:
                last = ""
                continue
            continues = (
                last
                and not last.endswith(_END)
                and not _LIST_ITEM.match(line)
                and (line[0].islower() or len(last) >= WRAP_CHARS)
            )
            if continues:
                groups[-1].append(line)
            else:
                groups.append([line])
            last = line
        passages += [
            Passage(passage_id=f"P{len(passages) + n}", page=page, text=" ".join(group))
            for n, group in enumerate(groups, start=1)
        ]
    return passages


def dates_in(text: str) -> list[date]:
    """Full dates written in the text, in order: `7 November 2026`, `07/11/2026` (day first, as
    in New Zealand) and `2026-11-07`. Partial or impossible dates are skipped."""
    found: list[date] = []
    for match in _DATE.finditer(text):
        if match["d"]:
            month = _MONTHS.get(match["month"].lower())
            parts = (match["y"], str(month or 0), match["d"])
        elif match["d2"]:
            parts = (match["y2"], match["m2"], match["d2"])
        else:
            parts = (match["y3"], match["m3"], match["d3"])
        try:
            found.append(date(*(int(p) for p in parts)))
        except ValueError:
            continue
    return found


def _iso(value: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _deadline(raw: RawDeadline | None, pages: Mapping[int, str]) -> Deadline:
    if raw is None:
        return Deadline(status="missing")
    due = _iso(raw.date)
    on_page = quote_on_page(raw.quote, pages.get(raw.page, ""))
    verified = due is not None and on_page and due in dates_in(raw.quote)
    return Deadline(
        status="verified" if verified else "unverified", due=due, quote=raw.quote, page=raw.page
    )


def apply_letter_rules(
    reading: LetterReading, passages: Sequence[Passage], pages: Mapping[int, str]
) -> LetterRead:
    """Validated concerns (`q1…`), the deadline, and every passage nothing accounted for."""
    known = {p.passage_id for p in passages}
    dropped: list[Dropped] = []
    concerns: list[LetterConcern] = []
    covered: set[str] = set()
    replaced = 0
    for raw in reading.concerns:
        if not raw.passages or not set(raw.passages) <= known:
            detail = f"{raw.summary!r}: {', '.join(raw.passages) or 'no passages'}"
            dropped.append(Dropped(reason="unknown_passage", detail=detail))
            continue
        if not quote_on_page(raw.quote, pages.get(raw.page, "")):
            dropped.append(
                Dropped(reason="citation_invalid", detail=f"letter p{raw.page} {raw.quote!r}")
            )
            continue
        summary = raw.summary
        if uses_banned_wording(summary):
            summary, replaced = f"INZ raises a concern in {', '.join(raw.passages)}", replaced + 1
        concerns.append(
            LetterConcern(
                finding_id=f"q{len(concerns) + 1}",
                summary=summary,
                passages=raw.passages,
                page=raw.page,
                quote=raw.quote,
            )
        )
        covered |= set(raw.passages)
    for passage_id in reading.context_passages:
        if passage_id in known:
            covered.add(passage_id)
        else:
            dropped.append(Dropped(reason="unknown_passage", detail=f"context: {passage_id}"))
    left = [p for p in passages if p.passage_id not in covered]
    unaccounted = [
        Unaccounted(finding_id=f"u{n}", passage_id=p.passage_id, page=p.page, text=p.text)
        for n, p in enumerate(left, start=1)
    ]
    return LetterRead(
        deadline=_deadline(reading.deadline, pages),
        concerns=concerns,
        unaccounted=unaccounted,
        dropped=dropped,
        replaced=replaced,
    )


def apply_evidence_rules(
    concerns: Sequence[LetterConcern],
    replies: Iterable[EvidenceReply],
    pages: PageTexts,
    failed: Collection[str],
    conflict_ids: Collection[str],
) -> tuple[list[Concern], list[Dropped], int]:
    """One evidence result per concern, in letter order (§8.8).

    `failed` are concerns whose model call failed after retries; `conflict_ids` are the
    findings of the consistency check whose conflicts were offered to the model.
    """
    known = {c.finding_id for c in concerns}
    dropped: list[Dropped] = []
    first = first_replies(replies, known, lambda r: r.concern_id, "concern", dropped)

    results: list[Concern] = []
    replaced = 0
    for concern in concerns:
        reply = first.get(concern.finding_id)
        citations: list[Citation] = []
        request: str | None = None
        related: list[str] = []
        downgraded: Downgrade | None = None
        if concern.finding_id in failed:
            status: EvidenceStatus = "unable"
            finding = "The evidence could not be matched (model call failed)"
            downgraded = "call_failed"
        elif reply is None:
            status, finding, downgraded = "unable", "not evaluated", "missing"
        else:
            citations = valid_citations(concern.finding_id, reply.citations, pages, dropped)
            status, finding, request = reply.status, reply.finding, reply.client_request
            if status in ("supported", "partial") and not citations:
                status, downgraded = "no_evidence", "no_valid_citation"
            for conflict_id in reply.conflict_ids:
                if conflict_id in conflict_ids:
                    related.append(conflict_id)
                else:
                    dropped.append(Dropped(reason="unknown_conflict", detail=conflict_id))
            if uses_banned_wording(finding):
                finding, replaced = EVIDENCE_TEMPLATE[status], replaced + 1
            if request is not None and uses_banned_wording(request):
                request, replaced = None, replaced + 1
        results.append(
            Concern(
                **concern.model_dump(),
                status=status,
                finding=finding,
                citations=citations,
                client_request=request,
                conflict_ids=related,
                downgraded=downgraded,
            )
        )
    return results, dropped, replaced


def require_letter(manifest: Manifest, doc_id: str | None) -> None:
    """A letter check replies to an INZ letter of this case, nothing else (§8.8)."""
    letter = manifest.document(doc_id or "")
    if letter is None or letter.source != "inz":
        raise Invalid(
            f"{doc_id or 'no document'} is not an INZ letter in this case; "
            "upload it as an INZ letter first",
            code="letter_invalid",
        )


def _long_date(day: date) -> str:
    return f"{day.day} {day.strftime('%B')} {day.year}"


def client_email(concerns: Sequence[Concern], deadline: Deadline) -> str:
    """The request to the client for what is missing; empty when nothing is requested."""
    asks = [c for c in concerns if c.client_request]
    if not asks:
        return ""
    lines = [
        "Hi,",
        "",
        "Immigration New Zealand has asked about some points in your application. "
        "To help us reply, please send us:",
        "",
        *(f"{n}. {c.client_request} (about: {c.summary})" for n, c in enumerate(asks, start=1)),
        "",
    ]
    if deadline.due is not None:
        lines.append(
            f"INZ needs our reply by {_long_date(deadline.due)}, "
            "so please send these as soon as you can."
        )
    else:
        lines.append("Please send these as soon as you can.")
    return "\n".join(lines) + "\n"


def reply_outline(
    letter_name: str,
    concerns: Sequence[Concern],
    names: Mapping[str, str],
    conflicts: Mapping[str, str],
) -> str:
    """One heading per concern with INZ's words and the verified sources; the argument is the
    adviser's to write."""
    blocks: list[str] = []
    for n, concern in enumerate(concerns, start=1):
        lines = [
            f"{n}. {concern.summary}",
            f'   INZ (page {concern.page}): "{concern.quote}"',
            f"   Evidence in the case: {_OUTLINE_LABEL[concern.status]}",
            *(
                f'   - {names.get(c.doc_id, c.doc_id)}, page {c.page}: "{c.quote}"'
                for c in concern.citations
            ),
            *(
                f"   Related conflict {c}: {conflicts[c]}"
                for c in concern.conflict_ids
                if c in conflicts
            ),
            "   [Adviser's response]",
        ]
        blocks.append("\n".join(lines))
    return f"Reply to INZ letter {letter_name}\n\n" + "\n\n".join(blocks) + "\n"


def working_days_until(due: date, today: date) -> int:
    """Monday-to-Friday days from tomorrow up to and including `due`; negative once overdue.

    Public holidays are not counted out (the UI says so); the adviser confirms the date.
    """
    start, end, sign = (today, due, 1) if due >= today else (due, today, -1)
    days = sum((start + timedelta(days=n)).weekday() < 5 for n in range(1, (end - start).days + 1))
    return sign * days
