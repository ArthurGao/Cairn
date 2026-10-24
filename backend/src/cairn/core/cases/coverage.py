"""What a check could not read is reported, never treated as clean (§8.5, §8.7, D-08)."""

from cairn.core.cases.models import CheckResult, Coverage, Gap, Manifest


def build_gaps(manifest: Manifest) -> list[Gap]:
    """One gap per failed document and one per document with unreadable pages (ids `g1…`)."""
    found: list[dict[str, object]] = []
    for doc in manifest.documents:
        unreadable = [p.n for p in doc.pages if p.method == "unreadable"]
        if doc.status == "failed":
            reason = doc.error or "document could not be ingested"
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
    return all(item.status == "checked" for item in result.items)
