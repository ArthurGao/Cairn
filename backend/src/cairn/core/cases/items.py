"""Pre-submission rules: every checklist item gets exactly one honest status (§8.5)."""

from collections.abc import Collection, Iterable, Mapping

from cairn.core.cases.citations import quote_on_page
from cairn.core.cases.models import (
    Citation,
    Downgrade,
    Dropped,
    ItemReply,
    ItemResult,
    ItemStatus,
)
from cairn.core.cases.spec import Checklist

PageTexts = Mapping[tuple[str, int], str]


def _valid_citations(
    item_id: str, citations: Iterable[Citation], pages: PageTexts, dropped: list[Dropped]
) -> list[Citation]:
    valid: list[Citation] = []
    for citation in citations:
        text = pages.get((citation.doc_id, citation.page))
        if text is not None and quote_on_page(citation.quote, text):
            valid.append(citation)
        else:
            dropped.append(
                Dropped(
                    reason="citation_invalid",
                    detail=f"{item_id}: {citation.doc_id} p{citation.page} {citation.quote!r}",
                )
            )
    return valid


def apply_item_rules(
    checklist: Checklist,
    replies: Iterable[ItemReply],
    pages: PageTexts,
    failed_items: Collection[str] = (),
) -> tuple[list[ItemResult], list[Dropped]]:
    """Results in checklist order, ids `i1…`.

    `failed_items` are items whose model call failed after retries (§8.7).
    """
    known = {item.id for item in checklist.items}
    dropped: list[Dropped] = []
    first_reply: dict[str, ItemReply] = {}
    for reply in replies:
        if reply.item_id not in known:
            dropped.append(Dropped(reason="unknown_item", detail=reply.item_id))
        elif reply.item_id in first_reply:
            dropped.append(Dropped(reason="duplicate_item", detail=reply.item_id))
        else:
            first_reply[reply.item_id] = reply

    results: list[ItemResult] = []
    for n, item in enumerate(checklist.items, start=1):
        reply = first_reply.get(item.id)
        citations: list[Citation] = []
        downgraded: Downgrade | None = None
        if item.id in failed_items:
            status: ItemStatus = "unable"
            finding = "The check could not be run for this item (model call failed)"
            downgraded = "call_failed"
        elif reply is None:
            status, finding, downgraded = "unable", "not evaluated", "missing"
        else:
            citations = _valid_citations(item.id, reply.citations, pages, dropped)
            status, finding = reply.status, reply.finding
            if status == "checked" and not citations:
                status, downgraded = "pending", "no_valid_citation"
        results.append(
            ItemResult(
                finding_id=f"i{n}",
                item_id=item.id,
                status=status,
                finding=finding,
                citations=citations,
                downgraded=downgraded,
            )
        )
    return results, dropped


def status_counts(items: Iterable[ItemResult]) -> dict[ItemStatus, int]:
    counts: dict[ItemStatus, int] = {"checked": 0, "pending": 0, "unable": 0}
    for item in items:
        counts[item.status] += 1
    return counts
