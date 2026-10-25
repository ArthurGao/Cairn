"""Quote verification: a citation counts only if its quote is on the cited page (D-16)."""

from collections.abc import Callable, Collection, Iterable, Mapping

from cairn.core.cases.models import Citation, Dropped

PageTexts = Mapping[tuple[str, int], str]


def normalise_ws(text: str) -> str:
    """Collapse every run of whitespace (incl. line breaks) to one space and trim."""
    return " ".join(text.split())


def quote_on_page(quote: str, page_text: str) -> bool:
    """True when the quote occurs in the page text after whitespace normalisation.

    Case-sensitive on purpose: a quote is a copy, not a paraphrase.
    """
    needle = normalise_ws(quote)
    return bool(needle) and needle in normalise_ws(page_text)


def valid_citations(
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


def first_replies[R](
    replies: Iterable[R],
    known: Collection[str],
    key: Callable[[R], str],
    what: str,
    dropped: list[Dropped],
) -> dict[str, R]:
    """The first reply per known id; unknown and repeated ids go to `dropped`."""
    first: dict[str, R] = {}
    for reply in replies:
        reply_id = key(reply)
        if reply_id not in known:
            dropped.append(Dropped(reason=f"unknown_{what}", detail=reply_id))
        elif reply_id in first:
            dropped.append(Dropped(reason=f"duplicate_{what}", detail=reply_id))
        else:
            first[reply_id] = reply
    return first
