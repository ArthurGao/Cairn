"""Quote verification: a citation counts only if its quote is on the cited page (D-16)."""


def normalise_ws(text: str) -> str:
    """Collapse every run of whitespace (incl. line breaks) to one space and trim."""
    return " ".join(text.split())


def quote_on_page(quote: str, page_text: str) -> bool:
    """True when the quote occurs in the page text after whitespace normalisation.

    Case-sensitive on purpose: a quote is a copy, not a paraphrase.
    """
    needle = normalise_ws(quote)
    return bool(needle) and needle in normalise_ws(page_text)
