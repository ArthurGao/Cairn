# Decisions

Each entry: the decision, why, and what would make us revisit it. Newest last. Reference as D-NN.

## D-01 — Files are the source of truth; no database in v1

**Decision.** Memory, skills, usage stats, change log and run records are files in the harness home.
Temporal keeps workflow progress. No Postgres/SQLite of our own.

**Why.** The point of the harness is that knowledge stays readable, diffable, portable and usable by
other tools (Claude Code, Codex) without an export step. A database would become a second source
of truth to keep in sync. The data is small (hundreds of files, a few KB each).

**Revisit when** a home exceeds ~5,000 memories, or multi-user editing is required.

## D-02 — Temporal for runs and cleanup

**Decision.** Agent runs and memory cleanups are Temporal workflows; every LLM call, tool call and
file write is an activity.

**Why.** An agent run is a chain of slow, failure-prone calls; Temporal retries an activity
instead of losing the run. The cleanup must wait days for a person — a durable timer plus a
signal is the native model, with no polling table or cron state of our own. Schedules give
single-flight (`SKIP` overlap) for free. Time-skipping test environments make the 6-day wait
testable in milliseconds.

**Cost accepted.** Workflow code must be deterministic; payloads must stay small (we truncate tool
results before they enter history).

## D-03 — One pure core library

**Decision.** `cairn.core` holds every rule about files (parse, validate, index, budget, write,
lint, similarity, secrets). It imports no Temporal, FastAPI or vendor SDK.

**Why.** The same rules must hold whether a write comes from a run, a cleanup, the API (undo) or the
CLI. One implementation is the only way they cannot drift, and it is unit-testable with plain
files. It is also what makes the CLI usable from other tools and git hooks.

## D-04 — Formats copied from Claude Code memory and Agent Skills

**Decision.** Memory files use Claude Code's memory frontmatter (`name`, `description`,
`metadata.type`) and index line format; skills use `SKILL.md` with `name`/`description`.

**Why.** Cross-tool reuse with zero conversion: the user already keeps skills in `~/.agents/skills`
(shared by Claude Code and Codex) and memories in Claude Code's format. Inventing a format would
force an importer and an exporter for no gain.

## D-05 — No write tool for the agent; write-back happens once, after the run

**Decision.** The runtime agent's tools are read-only. Memory changes are proposed in one
structured extraction step after the run and validated by code.

**Why.** A mid-run `write_memory` tool lets the model write unvalidated text at any moment and
makes retries dangerous (a retried step writes twice). A single post-run step sees the whole
transcript, can be validated against it (verbatim evidence), and is idempotent by `op_id`.

## D-06 — Usage stats in a sidecar file, not in memory frontmatter

**Decision.** Read counts and last-read dates live in `state/usage.json`.

**Why.** Updating frontmatter on every read would rewrite memory files constantly, flood the change
log and produce noisy git diffs in a home kept under version control.

## D-07 — Human approval for destructive cleanup; mechanical fixes auto-apply

**Decision.** `archive` and `merge` require approval in the UI; `index_sync` applies automatically.
Nothing is hard-deleted.

**Why.** Rewriting or retiring knowledge is a judgement with consequences — the model may draft it,
a person decides. Re-syncing the index with the files on disk is mechanical and fully determined
by the files, so asking would only train people to click "approve" without reading.

## D-08 — A failed step is never shown as an empty result

**Decision.** A failed extraction records `error` and is shown as failed; a check that could not run
is `null`, not "passed"; the API returns 503, not an empty list, when Temporal is unreachable.

**Why.** "Nothing to remember" and "extraction crashed" look identical if both render as an empty
list, and the second would go unnoticed for weeks.

## D-09 — Lexical similarity, no embeddings, in v1

**Decision.** Duplicate detection uses `rapidfuzz` token-set ratio with configured thresholds.

**Why.** Embeddings add a model dependency, cost and a vector store for an unmeasured gain, and
a weekly human-reviewed cleanup tolerates misses. Measured limit (design §7.2): a paraphrased pair
scored only 0.57 on descriptions and 0.74 on bodies, so the description check alone misses it and
the body threshold (0.70) catches it with a small margin over the nearest unrelated pair (0.53).
Lexical matching is therefore a floor, not a guarantee.

**Revisit when** cleanup reviews show people regularly merging pairs the check missed.

## D-10 — Conservative local token estimate; vendor numbers for accounting

**Decision.** Budgets use `ceil(chars / 3.5)`; recorded usage uses the vendor's reported counts.

**Why.** The budget is checked offline, in the CLI and in tests, without a network call, so it
needs a deterministic estimate. It errs high so a "within budget" claim holds against the real
tokenizer. Billing-grade numbers come from the response.

## D-11 — Ports 4700 (API), 4710 (web), 7233/8233 (Temporal)

**Why.** 3000–3003, 3100, 3400, 40xx, 5000, 5400–5402 and 8000–8002 are already used on the dev
machine by other projects. Temporal keeps its defaults (free on this machine).

## D-12 — Vercel AI Gateway for Claude and GPT, native protocol per family; direct Anthropic kept

**Decision.** Roles default to the `gateway` vendor (Vercel AI Gateway, one `AI_GATEWAY_API_KEY`),
which reaches `anthropic/*` models over the Anthropic Messages protocol and `openai/*` models over
OpenAI Chat Completions, each with its own SDK pointed at the gateway. The direct `anthropic`
vendor stays as a per-role alternative. Defaults remain Claude Sonnet 5.5; GPT is opt-in by config.

**Why.** The gateway gives one key, one bill and one request log for both model families, and
lets a role move between Claude and GPT without code. Speaking each family's native protocol,
rather than sending Claude through the OpenAI-compatible endpoint, keeps `effort`, structured
output and tool-use semantics exactly as each vendor documents them, at the cost of two adapters.
The Anthropic adapter is shared by the gateway and direct paths, so keeping the direct vendor costs
only a base URL and a key, and leaves a path if the gateway is down or a feature lags there.
No GPT default: no role has been evaluated on a GPT model.

**Revisit when** a role is evaluated on GPT (set the default from the result), when a third model
family is needed (consider the gateway's provider-neutral endpoint instead of a third adapter), or
when the direct path has gone unused for a quarter.

## D-13 — Case checks are fixed-step workflows, not agent loops

**Decision.** The consistency and pre-submission checks run as `CaseCheckWorkflow`: code visits
every document (map), every checklist item (batches), and decides what is accepted; the model only
drafts inside a step. The skill body and its reference files are loaded by code, not chosen by the
model.

**Why.** The product promise is "every document and every item was checked, and what could not be
is shown". In a free agent loop a model can skip a document and nothing shows it — the result looks
clean (the "no evidence read as pass" failure in the KB's `llm-app-architecture.md` §4.2, §6.2).
Fixed steps make coverage a property of code, testable with exact counts, while checklists and
fact categories stay editable by advisers as skills.

**Revisit when** a check needs open-ended investigation that a fixed sequence cannot express; then
add a bounded agent step inside the workflow, still with coverage enforced around it.

## D-14 — Client documents live in a case store outside the harness home

**Decision.** `CAIRN_CASES_DIR` holds cases (originals, pages, results, audit); the harness home
holds only cross-case knowledge. The worker refuses a case store inside the home, and write-back
rejects personal-data patterns (`personal_data`).

**Why.** The harness home is meant to be versioned, shared with Claude Code/Codex and copied
between machines; client documents must never travel with it. Separate directories make the rule
structural rather than a convention.

## D-15 — Data-class gate: synthetic data only until Azure Australia is verified

**Decision.** `CAIRN_DATA_CLASS` is `synthetic` by default. `client` requires every role's vendor to
be allow-listed, and v1 refuses `gateway` and `anthropic` in that list, so v1 cannot process client
data. The `azure` vendor is reserved for that path.

**Why.** The proposal's legal baseline: written client consent before personal information enters
an AI system (OMARA), and data residency in Australia must be verified — processing, logs,
backups and abuse monitoring — not assumed from "it runs in our Azure account". Development and
the pilot's first phase use synthetic cases through the gateway; a config switch must not be able
to send a real client's documents to an unverified vendor.

**Revisit when** the Azure deployment's locations are verified and consent is recorded per case.

## D-16 — Documents are stored as pages; scans are transcribed by a model; citations are verified against page text

**Decision.** Ingest turns every document into page files: the PDF text layer where present, a
model transcription (`document.transcribe`) where not, or `unreadable` with a reason. Every fact
and finding cites `(doc_id, page, quote)`, and code accepts it only if the quote is on that page.

**Why.** Advisers work by page ("employer letter, page 1"), and page-level citations are what make
a finding checkable. Verifying quotes in code turns "the model says the document says" into a
mechanical check.

**Cost accepted.** For transcribed pages the quote is verified against the transcription, not the
image; such pages are badged "transcribed by model" and the adviser checks the original.

## D-17 — Visual direction: swiss-grid, with dense-data detail

**Decision.** The UI uses the design KB's swiss-grid direction (layout, type, palette) with
dense-data's numeric and table conventions as local detail; one non-red accent.

**Why.** The UI is used two ways at once: reading findings and quotes at length, and working
through review queues. Swiss-grid is the KB direction that covers both reading and operating;
refined-saas (dark, developer-tool feel) suits operating only, and warm-humanist avoids density.
Red is reserved for conflicts and diffs, so the Swiss red accent is replaced by a single other
colour.

## D-18 — Docker runs only the Temporal dev server; the worker, API and web stay on the host

**Decision.** `docker-compose.yml` has one service: the Temporal dev server
(`temporalio/temporal`, pinned to the CLI's version, ports 7233/8233, SQLite in a named volume).
The worker, API and web are started on the host (`make dev-app` or one target each).

**Why.** The worker and the API both write the harness home and the case store, and they rely on
`filelock` for the home and case locks (§6.4). On macOS, locks taken inside a container on a
bind-mounted directory are not guaranteed to be seen by a host process, so a containerised worker
and a host API could write the same file at once. Temporal shares nothing on disk with them.

**Revisit when** the worker and the API run in the same place (both in containers on one Linux
host, or a deployment with its own storage), at which point all of them can be containerised.

