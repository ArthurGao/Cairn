---
name: case-consistency-check
description: Find facts that conflict across a case's documents (dates, addresses, employment, family, travel, prior applications), each with both sources and pages and a question to confirm. Use when asked to cross-check or reconcile a case file.
---

# Case consistency check

Used by the consistency check workflow (code runs the steps; you draft each step's output).

1. **Extract facts, one document at a time.** For every fact in a category listed in
   `references/fact-categories.md`, record the category, the person it is about, the value as
   written, a normalised value, and the page and an exact quote that shows it. Copy the quote
   character for character; a quote that is not on that page is discarded.
2. Record what the document says, not what you expect. A date you cannot read is not a fact.
3. **Compare.** A conflict is the same fact about the same person stated differently in two or
   more documents. Dates at different precision (`2022-03` and `2022-03-14`) agree.
4. For each conflict write one neutral question, e.g. "The questionnaire gives a start date of
   March 2022; the employer letter (page 1) gives June 2022. Which is correct?"
5. Never say which version is right, and never suggest a document is false.
