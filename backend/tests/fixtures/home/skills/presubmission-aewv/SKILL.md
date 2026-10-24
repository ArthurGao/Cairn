---
name: presubmission-aewv
description: Final completeness check of an Accredited Employer Work Visa (AEWV) application against the adviser's checklist; every item is checked, pending or unable to check, with sources. Use before an AEWV application is submitted.
---

# Pre-submission check — AEWV

Used by the pre-submission check workflow. Code loads `references/checklist.yaml` and sends you
the items; you judge each item against the case documents.

1. For each item return exactly one status:
   - **checked** — the documents show the item is satisfied; cite the page and quote.
   - **pending** — something is missing or unresolved; say what, and cite what you did find.
   - **unable** — you cannot tell (page unreadable, document absent, judgement needs the adviser).
2. A result without a valid citation is not **checked**; code downgrades it to **pending**.
3. Judge completeness only. Whether the applicant is eligible is the adviser's decision.
4. Rules and thresholds come from the checklist, never from what you remember about INZ policy.
