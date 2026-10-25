"""What a check could not read is reported, never treated as clean (§8.5, §8.7, D-08)."""

from collections.abc import Mapping

from cairn.core.cases.items import status_counts
from cairn.core.cases.models import CheckResult, Coverage, Gap, Manifest


def in_scope(manifest: Manifest, letter_doc_id: str | None = None) -> Manifest:
    """The documents a check covers: the client's evidence, plus the one INZ letter a letter
    check replies to (§8.8). Other INZ letters are neither ingested nor reported."""
    documents = [d for d in manifest.documents if d.source == "client" or d.doc_id == letter_doc_id]
    return manifest.model_copy(update={"documents": documents})


def check_counts(result: CheckResult) -> dict[str, int | bool]:
    """The counts shown for a check, never one pass/fail (§12.2); one definition for the
    workflow summary and the API."""
    counts = status_counts(result.items)
    concerns = result.letter.concerns if result.letter else []
    return {
        "conflicts": len(result.conflicts),
        **counts,
        "concerns": len(concerns),
        "not_supported": sum(c.status != "supported" for c in concerns),
        "gaps": len(result.gaps),
        "clean": is_clean(result),
    }


def build_gaps(manifest: Manifest, check_failures: Mapping[str, str] | None = None) -> list[Gap]:
    """One gap per failed document and one per document with unreadable pages (ids `g1…`).

    `check_failures` are documents ingested fine whose check step failed (e.g. extraction).
    """
    failures = check_failures or {}
    found: list[dict[str, object]] = []
    for doc in manifest.documents:
        unreadable = [p.n for p in doc.pages if p.method == "unreadable"]
        if doc.status != "ingested" or doc.doc_id in failures:
            reason = (
                doc.error
                or failures.get(doc.doc_id)
                or ("document was not ingested" if doc.status == "pending" else "ingest failed")
            )
            found.append({"doc_id": doc.doc_id, "kind": "failed", "reason": reason})
        elif unreadable:
            reason = f"{doc.filename}: {len(unreadable)} page(s) could not be read"
            found.append(
                {"doc_id": doc.doc_id, "kind": "unreadable", "pages": unreadable, "reason": reason}
            )
    return [Gap.model_validate({"finding_id": f"g{n}", **g}) for n, g in enumerate(found, 1)]


def build_coverage(manifest: Manifest, facts_accepted: int = 0, facts_dropped: int = 0) -> Coverage:
    pages = [p for d in manifest.documents for p in d.pages]
    return Coverage(
        documents=len(manifest.documents),
        documents_failed=sum(d.status == "failed" for d in manifest.documents),
        pages=len(pages),
        pages_transcribed=sum(p.method == "transcribed" for p in pages),
        pages_unreadable=sum(p.method == "unreadable" for p in pages),
        facts_accepted=facts_accepted,
        facts_dropped=facts_dropped,
    )


def is_clean(result: CheckResult) -> bool:
    """Clean only when nothing is open and nothing went unread."""
    if result.status != "completed" or result.gaps:
        return False
    if result.kind == "consistency":
        return not result.conflicts
    if result.kind == "letter":
        letter = result.letter
        return (
            letter is not None
            and letter.deadline.status == "verified"
            and not letter.unaccounted
            and all(c.status == "supported" for c in letter.concerns)
        )
    return all(item.status == "checked" for item in result.items)
