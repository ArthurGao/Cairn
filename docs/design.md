# Cairn — design

Status: approved for v1 build · 2026-10-24 (revised the same day: Vercel AI Gateway, adviser case
checks). Sections are numbered; cite them as "design §N".
Decisions with their reasons are in [`decisions.md`](decisions.md) (D-NN).

---

## 1. Purpose

Licensed immigration advisers spend much of each week cross-checking documents and preparing
applications — work that is slow, repetitive and exactly where a missed conflict turns into an
INZ request for more information. Cairn is the harness for agents that do that groundwork and hand
a draft to the adviser, who decides. The first three jobs (from the adviser-agent proposal):

- **Case consistency check** — read every document in a case and list the facts that conflict
  (dates, addresses, employment, family, travel, prior applications), each with both sources,
  page and quote, and a neutral question to confirm.
- **Pre-submission check** — check a case against the adviser's checklist for its visa type; every
  item comes back *checked*, *pending* or *unable to check*, with sources.
- **INZ letter reply** — read a potentially prejudicial information letter or request for
  information, check its reply deadline, list every concern INZ raises, and map each to the
  evidence already in the case, with an email asking the client for what is missing and a reply
  outline for the adviser to write from (§8.8).

Underneath, Cairn keeps the agents' long-lived knowledge as **plain files** and shows a model only
an **index** up front; detail is loaded on demand. After each run the harness **writes back** what
was learned, and a **scheduled cleanup** stops the files from rotting.

What makes it worth building rather than "a script that calls a model":

- **Coverage is guaranteed by code.** A check visits every document and every checklist item; what
  it could not read or judge is shown as such, never as clean.
- **Every finding carries its evidence.** Each fact and finding cites a document, page and a quote
  that code has verified is on that page.
- **The model drafts; the adviser decides.** Nothing goes to a client or INZ; every adviser
  decision is logged.
- **Low token by construction.** The always-loaded context has a budget enforced in code.
- **Durable.** Runs and checks are Temporal workflows: an LLM outage or worker restart resumes the
  work instead of losing it; a cleanup can wait days for a human decision.
- **Portable knowledge.** Skills (checklists, fact categories) and memories use the Claude Code /
  Agent Skills formats; the same harness home works in Cairn, Claude Code and Codex.

## 2. Goals, non-goals, anti-goals

**Goals (v1)**

1. Feature C — case checks: consistency and pre-submission, with verified citations and adviser
   review (§8). **The pilot's reason to exist.**
2. Feature A — a general agent run that uses progressive disclosure and ends with validated
   write-back (§6).
3. Feature B — a weekly memory cleanup that proposes changes and applies only approved ones (§7).
4. A web UI: cases and check results first; runs, memory, skills and cleanup under "Manage" (§12).
5. A CLI that runs the same lint/index/context code outside the app (§9.3).

**Non-goals (v1; leave seams, do not build)**

- Immigration advice of any kind: eligibility, what to apply for, which document is right.
- Spouse-visa evidence organisation, enquiry intake and the other agents in the proposal. They
  reuse Feature C's document pipeline later. (INZ letter replies are built: §8.8.)
- Real client data. v1 runs on synthetic or anonymised documents only, enforced by the data-class
  gate (§10.4), until processing in Azure Australia is verified.
- Multi-user, auth, multi-tenant homes. One harness home and one case store per deployment, local
  use. Adviser sign-off records a typed name, not an authenticated identity.
- Skill authoring by the agent, or skill write-back. Skills are read-only in v1.
- Embeddings / vector search. Similarity is lexical (§7.2).
- Agents taking actions in the outside world. Agents have read-only tools only.

**Anti-goals (a failure even if it "works")**

- A check that reports "no issues" for a document or item it did not actually read or judge.
- A finding without a source a person can open, or with a quote that is not on the cited page.
- Wording that decides which version is right or suggests a document is false.
- Client data in the harness home (memory, skills, run records), or sent to a vendor the
  data-class gate does not allow.
- Memory that grows without bound, or an index that silently exceeds its budget.
- A write the user cannot see, explain or undo.
- A cleanup that deletes or rewrites knowledge without a person approving it.
- A secret (API key, password, private key) written into a memory file.
- Business code that names a model or vendor.

## 3. Storage

Two directories with different rules: the **harness home** holds knowledge and is safe to share
and version; the **case store** holds client documents and never leaves the deployment (D-14).

### 3.1 Harness home

A directory; its path comes from `CAIRN_HOME`. In dev it is the repo's `workspace/`; in tests it
is a copy of `backend/tests/fixtures/home/` in `tmp_path`. M0 creates the fixture home as a copy
of `workspace/` (which already contains a planted duplicate pair and a stale memory for Feature B);
after that the two evolve separately and tests depend only on the fixture.

```
<home>/
  AGENTS.md                    # runtime agent's always-loaded instructions (L0)
  memory/
    MEMORY.md                  # memory index: one line per memory (L0)
    <slug>.md                  # one memory per file (L1)
    _archive/<slug>.md         # archived memories (never loaded; restorable)
    _changelog.jsonl           # append-only log of every write (before/after)
  skills/
    <skill-name>/
      SKILL.md                 # frontmatter = L0 entry; body = L1
      references/*             # L2, loaded by explicit path (e.g. checklist.yaml)
  state/
    usage.json                 # per-memory read stats (sidecar; never in frontmatter)
    runs/<YYYY-MM-DD>-<run_id>.md  # run records written back after each run
  .cairn.lock                  # home-wide write lock (filelock)
```

Extra **read-only skill sources** can be mounted with `CAIRN_SKILL_PATHS` (colon-separated),
e.g. `~/.agents/skills`. Skills found there are listed and loadable exactly like local ones but are
never written. A name collision is resolved local-first and reported by `cairn lint` (§7.2).

### 3.2 Case store

A directory; its path comes from `CAIRN_CASES_DIR` (dev: `.cases/` at the repo root, gitignored;
tests: `tmp_path`). It must not be inside the harness home; the worker refuses to start if it is.

```
<cases>/<case_id>/
  case.json                    # manifest (§4.7)
  originals/<doc_id>.<ext>     # uploaded files, byte-for-byte, never modified
  pages/<doc_id>/p<NNNN>.md    # one file per page: text + how it was obtained (§4.8)
  checks/<check_id>.json       # check results, immutable once written (§4.9)
  _audit.jsonl                 # adviser review actions and sign-off (§4.10)
  .case.lock
```

`case_id`, `doc_id` and `check_id` are ULIDs generated by the API. A case's `label` is free text
chosen by the adviser.

Files are the source of truth in both places; Temporal stores workflow progress; there is no
database (D-01).

## 4. File formats

All Markdown files are UTF-8 with YAML frontmatter parsed by `yaml.safe_load`. Unknown
frontmatter keys are preserved on rewrite (another tool may own them).

### 4.1 Memory file — `memory/<slug>.md`

Same shape as Claude Code memory files, so they can be copied either way.

```markdown
---
name: conflicts-as-questions
description: Phrase each conflict as a question to confirm; never as an accusation
metadata:
  type: feedback            # user | feedback | project | reference
  created: 2026-10-24
  updated: 2026-10-24
  source_run: 01JB...       # run that created/last updated it (absent if hand-written)
---

Write every conflict as a neutral question the adviser can put to the client.

**Why:** most conflicts are typos or a different date convention.
**How to apply:** state both versions with their sources, then ask which is right.
Related: [[intake-form-v1-dates]]
```

Rules (enforced by `core.formats`, reported by lint):

- `name` = file stem, kebab-case, `^[a-z0-9]+(-[a-z0-9]+)*$`, ≤ 64 chars.
- `description` one line, ≤ 150 chars — it is what the agent sees in the index, so it must say
  *when the memory is relevant*.
- `metadata.type` in the four types. `feedback` and `project` bodies should have **Why** and
  **How to apply** lines (lint warning, not error).
- Body ≤ 2,000 characters. Longer knowledge is a skill, not a memory.
- `[[slug]]` links may point to memories that do not exist yet; that is allowed, not an error.
- Memory holds knowledge that applies across cases (adviser preferences, wording rules, form
  quirks), never a client's facts (§6.3 `personal_data`).

### 4.2 Memory index — `memory/MEMORY.md`

```markdown
# Memory

- [Conflicts as questions](conflicts-as-questions.md) — Phrase each conflict as a question to confirm; never as an accusation
- [Pilot scope](pilot-scope.md) — Pilot covers AEWV cases only, on synthetic documents until Azure AU is verified
```

- One line per memory: `- [<Title>](<slug>.md) — <description>`. No frontmatter, no memory content.
  `<Title>` = `metadata.title` if present, else the slug with hyphens replaced by spaces and the
  first letter upper-cased (`pilot-scope` → `Pilot scope`).
- The index is **regenerated by code** from the memory files (`core.index.render_memory_index`):
  a `# Memory` heading, a blank line, then lines ordered by type (`user`, `feedback`, `project`,
  `reference`) and then by slug. Hand edits survive only until the next write; lint reports drift.
  The sample `workspace/memory/MEMORY.md` is byte-identical to this rendering — use it as the
  golden file for the renderer test.
- Budget: `CAIRN_MEMORY_INDEX_BUDGET` tokens (default 1,500). Over budget is a lint error and
  shown in the UI; the context builder then includes `user` and `feedback` lines first and states
  how many lines were omitted (never truncates silently).

### 4.3 Skill — `skills/<name>/SKILL.md`

The Agent Skills format (as used by Claude Code and Codex):

```markdown
---
name: case-consistency-check
description: Find facts that conflict across a case's documents ... Use when asked to cross-check or reconcile a case file.
---

# Case consistency check
...body: steps, rules; may reference files under references/ by relative path...
```

- `name` = directory name; `description` ≤ 300 chars and must say when to use the skill.
- `references/` files are L2: only reachable through `read_skill_file(name, path)` or loaded by
  code for a check (§8), and only inside that skill's directory (path traversal is rejected).
- Two skills drive Feature C, and their reference files are parsed by code (`core.cases`):
  - `case-consistency-check/references/fact-categories.md` — the table's backticked first
    column is the list of fact categories; it becomes the extraction schema's enum.
  - `presubmission-<visa>/references/checklist.yaml` — `{visa, version, owner, items: [{id,
    requirement, verify}]}`; `id` unique, kebab-case. Any skill named `presubmission-*` with a valid
    checklist is offered as a pre-submission check type. Advisers maintain these files; rules and
    thresholds live there, never in prompts or code.

### 4.4 Usage sidecar — `state/usage.json`

```json
{ "conflicts-as-questions": { "reads": 7, "last_read": "2026-10-22", "written_by_runs": 2 } }
```

Updated deterministically after each run for every memory the agent read (§6.2). Kept out of the
memory files so reads do not churn them (D-06). Missing entry = never read.

### 4.5 Change log — `memory/_changelog.jsonl`

One JSON object per write, appended under the lock:

```json
{"id":"chg_01JB...","op_id":"<run_id>:0","at":"2026-10-24T03:12:09Z","actor":"run:01JB...|cleanup:01JB...|user|cli",
 "op":"create|update|archive|restore|index_sync","slug":"conflicts-as-questions",
 "before":null,"after":"---\nname: ...","base_hash":null,"reason":"..."}
```

Extra fields: `group_id` (ops applied together — one write-back run, one merge — share it) and
`undo_of` (set on entries written by an undo). `before`/`after` are full file texts at
`memory/<slug>.md`, or `null` when no file exists there (create: `before: null`; archive:
`after: null`, the text having moved to `_archive/<slug>.md`). The log is never edited.

**Undo** takes a change id and undoes its **whole group**, newest entry first, as one new group
whose entries carry `undo_of`. Each entry's inverse:

| Original op | Inverse written | Precondition (else 409 `conflict`, nothing undone) |
| --- | --- | --- |
| `create` | `archive` | current file hash = hash(after) |
| `update` | `update` back to `before` | current file hash = hash(after) |
| `archive` | `restore` (move `_archive/<slug>.md` back) | archived file hash = hash(before) and no live file at the slug |
| `restore` | `archive` | current file hash = hash(after) |
| `index_sync` | not undoable (re-derivable); excluded from groups others can undo | — |

So undoing a merge restores the target's old text *and* un-archives the other members together.

Two edge cases: an `archive` onto a slug that already has `_archive/<slug>.md` is a `conflict`
(an archived version is never overwritten); and an `update` whose log line was written only after a
crash (§6.4 step 2a) has `before: null` — its old text is gone — so undoing its group returns 409
`not_undoable` instead of guessing.

### 4.6 Run record — `state/runs/<date>-<run_id>.md`

```markdown
---
run_id: 01JB...
started: 2026-10-24T03:10:02Z
status: completed            # completed | failed
tokens: { l0: 1840, loaded: 2310, baseline_all: 19400, input_total: 9120, output_total: 1430 }
loaded: [skill:presubmission-aewv, memory:pilot-scope]
writeback: { applied: 2, rejected: 1 }
---

## Task
...
## Outcome
...one-paragraph summary drafted by memory.extract...
## Open items
- ...
```

### 4.7 Case manifest — `<cases>/<case_id>/case.json`

```json
{ "case_id": "01JB...", "label": "AEWV sample 1", "created": "2026-10-24T03:00:00Z",
  "data_class": "synthetic",
  "documents": [
    { "doc_id": "01JB...", "filename": "employer-letter.pdf", "stored_name": "01JB....pdf",
      "media_type": "application/pdf",
      "bytes": 48211, "sha256": "...", "uploaded": "2026-10-24T03:01:10Z",
      "status": "pending|ingested|failed", "error": null,
      "pages": [ { "n": 1, "method": "text|transcribed|unreadable" } ],
      "source": "client|inz" } ] }
```

`source` (default `client`) is set at upload: `inz` marks a letter from INZ. A letter check reads
only the letter it replies to; no other check ingests or reports an `inz` document, and no check
uses one as evidence (§8.8).

Written by `core.cases` under `.case.lock` with atomic replace. Ids are plain
`[A-Za-z0-9_-]{1,64}` (they become path parts); adding a document is idempotent per `doc_id`
(same bytes → the stored document; different bytes → 409 `document_exists`). `data_class` is copied from
`CAIRN_DATA_CLASS` when the case is created and never changes (§10.4). Accepted uploads (v1):
PDF, PNG, JPEG, plain text and Markdown; anything else is rejected at upload with `unsupported_type`.

### 4.8 Page file — `pages/<doc_id>/p<NNNN>.md`

```markdown
---
doc_id: 01JB...
page: 1
method: text                 # text | transcribed | unreadable
source_sha256: ...           # hash of the original; a changed original re-ingests
model: null                  # set when method = transcribed (role document.transcribe)
reason: null                 # set when method = unreadable
---

...the page's text...
```

- `text`: extracted from a PDF's text layer (`pypdfium2`), or a text/Markdown file (one page).
- `transcribed`: a page whose text layer has fewer than `CAIRN_MIN_PAGE_CHARS` (40) characters, or
  an image, rendered and transcribed by role `document.transcribe`. Shown as "transcribed by
  model" everywhere; citations to it are verified against the transcription, not the image (D-16).
- `unreadable`: the transcription role reports it cannot read the page, or the file cannot be
  parsed. The body is empty and `reason` says why. Unreadable pages are listed in every check
  result; they are never treated as empty pages that "contain no conflicts".

### 4.9 Check result — `checks/<check_id>.json`

```json
{ "check_id": "01JB...", "case_id": "01JB...", "kind": "consistency|presubmission|letter",
  "checklist": { "skill": "presubmission-aewv", "version": "0.1-sample" },
  "started": "...", "finished": "...", "status": "completed|failed", "error": null,
  "coverage": { "documents": 6, "documents_failed": 0, "pages": 14, "pages_transcribed": 2,
                "pages_unreadable": 1, "facts_accepted": 41, "facts_dropped": 3 },
  "facts": [ { "fact_id": "f12", "category": "employment.period", "subject": "applicant",
               "qualifier": "Kauri Logistics Ltd", "value": "March 2022 – present",
               "normalised": "2022-03/..", "doc_id": "...", "page": 2, "quote": "..." } ],
  "conflicts": [ { "finding_id": "c1", "fact_ids": ["f12", "f30"], "origin": ["rule", "model"],
                   "summary": "...", "question": "...", "drafted_by": "model|template" } ],
  "items": [ { "finding_id": "i3", "item_id": "referenced-attachments-exist",
               "status": "checked|pending|unable", "finding": "...",
               "citations": [ { "doc_id": "...", "page": 1, "quote": "..." } ],
               "downgraded": null } ],
  "gaps": [ { "finding_id": "g1", "doc_id": "...", "kind": "unreadable|failed", "pages": [3],
              "reason": "bank-statement.pdf: 1 page(s) could not be read" } ],
  "dropped": [ { "reason": "citation_invalid|unknown_category|bad_normalised|...", "detail": "..." } ],
  "wording_replacements": 0,
  "calls": [ { "role": "...", "vendor": "...", "model": "...", "tokens_in": 0, "tokens_out": 0 } ] }
```

`conflicts` is set for `consistency`, `items` for `presubmission`, `letter` for `letter`
(§8.8: `{doc_id, related_check_id, deadline: {finding_id: "d1", status: verified|unverified|missing,
due, quote, page}, concerns: [{finding_id: "q1", summary, passages, page, quote, status:
supported|partial|no_evidence|unable, finding, citations, client_request, conflict_ids,
downgraded}], unaccounted: [{finding_id: "u1", passage_id, page, text}], client_email,
reply_outline}`); `gaps` (one per failed
document, one per document with unreadable pages) is set for both, so what could not be checked is
a finding the adviser settles like any other. Written once by the workflow's last activity (temp
file + rename); never edited — adviser review lives in `_audit.jsonl`.

### 4.10 Case audit log — `<cases>/<case_id>/_audit.jsonl`

```json
{"at":"2026-10-24T04:10:00Z","check_id":"01JB...","finding_id":"c1","action":"confirmed|dismissed|resolved|reopened","note":"Asked client 24 Oct","adviser":"A. Adviser"}
{"at":"2026-10-24T04:30:00Z","check_id":"01JB...","finding_id":null,"action":"signed_off","note":null,"adviser":"A. Adviser"}
```

Append-only, under `.case.lock`. A finding's current review state is its last entry. `dismissed`
always needs a note. `signed_off` is accepted only when every finding that needs review — every
conflict, every item that is not `checked`, every gap — is currently `confirmed`, `dismissed` or
`resolved` (`reopened` or no entry blocks). A `checked` item does not block sign-off; it is shown
with its citations. The `adviser` field is a typed name in v1 (no auth, §2).

## 5. Progressive disclosure

Three levels. Only L0 is in the first prompt of an agent run (Feature A). Feature C's workflows
load their skill's body and reference files by code, not by model choice, because coverage must not
depend on what a model decides to read (D-13); they still count those tokens.

**L0 over budget.** `AGENTS.md` and the skill index are never trimmed. If they alone exceed
`CAIRN_L0_BUDGET`, `build_context` raises `ContextBudgetError` (the run fails with that message;
`cairn lint` reports it as an error). Otherwise the memory index gets the remaining budget, trimmed
per §4.2 with `omitted_index_lines` set.

| Level | What | How it reaches the model | Budget (default, env-overridable) |
| --- | --- | --- | --- |
| L0 | home `AGENTS.md`; memory index lines; skill `name — description` lines | system prompt built by `build_context` | total `CAIRN_L0_BUDGET` = 4,000 tokens |
| L1 | a memory body; a `SKILL.md` body | tool call `read_memory(slug)`, `load_skill(name)` | each result ≤ 8,000 chars, else cut with a marker saying so |
| L2 | a file under a skill's `references/` | tool call `read_skill_file(name, path)` | ≤ 20,000 chars per call, same marker |

- Token counts are **estimates** (`ceil(chars / 3.5)`, deliberately conservative). Real usage comes
  from the vendor's response and is recorded per call; the UI labels which is which.
- `build_context` returns a `ContextBreakdown` (tokens per part) and the **baseline**:
  `baseline_all = AGENTS.md + every memory body + every SKILL.md body` (estimated tokens), i.e. the
  cost of loading everything eagerly instead of through indexes. The memory index in L0 is rendered
  from the memory files (the same rendering as `MEMORY.md`), so a hand-edited `MEMORY.md` cannot
  put stale lines in front of the agent; drift is a lint finding. The run
  timeline shows `l0 + loaded` against `baseline_all`. Compute it in code, test it with exact values
  on the fixture home.
- The system prompt tells the model: the index is a table of contents; load a skill before doing
  a task it covers; read a memory only when its description is relevant; do not ask for
  everything.
- Tools are read-only. There is no `write_memory` tool: write-back happens once, after the run,
  through validation (§6.3, D-05).

## 6. Feature A — agent run with state write-back

A general run: an adviser asks a question or a drafting task that is not a case check (e.g. "draft
a covering note listing these attachments"). Runs do not read the case store in v1.

### 6.1 Flow

```
POST /api/runs {task}
  -> start AgentRunWorkflow(run_id)            (workflow id = "run-<run_id>")
       build_context            activity   -> system prompt + ContextBreakdown
       loop (max_steps, default 8):
         llm_call(role=agent.main)   activity
         for each tool_use: run_tool  activity  (read_memory | load_skill | read_skill_file)
         stop when the reply has no tool_use
       extract_writeback(role=memory.extract)  activity -> WritebackProposal
       apply_writeback          activity   -> validated ops applied, rejected ops with reasons
       record_run               activity   -> run record file + usage.json update
  query get_state  -> RunState (steps so far, token breakdown, write-back result)
```

Workflow code is deterministic: no I/O, no clock, no randomness; everything above that touches a
file or the network is an activity. `run_id` is a ULID generated by the API before start.

### 6.2 RunState (query result, also the API's run view)

```
RunState {
  run_id, task, status: running|extracting|writing|completed|failed, error?: str
  context: ContextBreakdown { agents_md, memory_index, skill_index, l0_total, baseline_all, omitted_index_lines }
  steps: [ Step { n, kind: llm|tool, role?, tool?, arg?, result_chars?, truncated?, tokens_in?, tokens_out?,
                  tokens?, model?, at } ]          # tokens: tool steps, estimated, of what the model saw
  loaded: [ "skill:<name>" | "memory:<slug>" | "skillfile:<name>/<path>" ]
  loaded_tokens: int                       # estimated; sum of the tool steps' tokens (run record tokens.loaded)
  answer?: str
  writeback?: WritebackResult { applied: [AppliedOp { change_id, op, slug, before?, after?, undone }],
                                rejected: [RejectedOp], error?: str }
}
```

`read_hashes` (slug → sha256 of the text `read_memory` returned) stays local to the workflow; it
feeds write-back base hashes (§6.3) and is not part of the run view. `undone` is false in the
workflow result; `GET /api/runs/{run_id}` fills it from the change log, which outlives the run.

`at` comes from `workflow.now()`, never the system clock.

### 6.3 Write-back: what the model proposes, what code accepts

`extract_writeback` sends the task, final answer, the tool transcript (tool results truncated to
2,000 chars each) and the **current memory index** to role `memory.extract`, with structured
output:

```
WritebackProposal {
  ops: [ { op: create|update, slug, type, description, body, evidence: [str], reason } ]   # no schema max; see run_limit
  run_summary: str      # ≤ 800 chars, for the run record
  open_items: [str]
}
```

The prompt says: propose only facts that will matter in a *future* session (preferences,
corrections, wording rules, pointers); prefer `update` of an existing slug over a new
near-duplicate; never record secrets or any client's personal details; an empty list is a good
answer.

**Base hashes.** The model never supplies hashes. `read_memory` returns the file's SHA-256 with its
text, and the workflow keeps `read_hashes[slug]`. When `extract_writeback` returns, each `update`
op gets `base_hash = read_hashes[slug]` if the run read that memory, else the hash of the file at
extraction time (taken inside the activity). `conflict` therefore means "changed after the run read
it, or after extraction"; tests can trigger it by editing the fixture file between the
`read_memory` step and `apply_writeback`.

`apply_writeback` validates each op in order. The first failing rule rejects the op with that
rule's code; other ops still proceed:

| Code | Rule |
| --- | --- |
| `run_limit` | checked first: ops after the 5th are rejected unread; the first 5 continue |
| `schema` | slug/type/description/body satisfy §4.1 |
| `evidence_missing` | every `evidence` string occurs verbatim (whitespace-normalised) in the task, answer or transcript; at least one is required |
| `secret` | body and description match none of the secret patterns (`core.secrets`: `sk-ant-`, `sk-`, `AKIA`, `ghp_`, `xox[bp]-`, `-----BEGIN`, `password\s*[:=]`, long base64/hex runs ≥ 40 chars) |
| `personal_data` | body and description match none of the personal-data patterns (`core.secrets`: email addresses, phone numbers of ≥ 8 digits, passport-like ids `[A-Z]{1,2}\d{6,9}`, full dates of birth next to "born"/"DOB"/"date of birth") |
| `duplicate` | `create` whose description similarity (§7.2) to an existing memory ≥ `CAIRN_DUP_THRESHOLD` (0.82) → rejected and named in the reason; cleanup handles it later |
| `not_found` | `update` of a slug that does not exist |
| `conflict` | the file changed since the run read it (base hash mismatch, §6.4) |

Accepted `create` ops get `created`/`updated`/`source_run` set by code; `update` ops keep `created`
and unknown frontmatter keys and replace description/body. The model never sets dates. The rules
live in `core.validate.plan_writeback` (one op group per accepted op, op id `<run_id>:<index>`);
the writer's base-hash rejections come back as `conflict` via `conflict_rejections`.

### 6.4 Write protocol (shared by write-back, cleanup, undo, CLI)

`core.writer.apply(home, groups, actor)` — input is a list of **op groups**; a group is
all-or-nothing (a write-back op is a group of one; a merge is one group of `update` + `archive`s):

1. Acquire `<home>/.cairn.lock` (`filelock`, timeout 10 s → `LockTimeout`, retryable).
2. For each group, for each op, in this order:
   a. **Already applied?** If the op's `op_id` (`<run_id>:<index>`, or `<wf_id>:<op>`) is in the
      changelog → skip it. If not, but the target's current hash equals hash(op.after) → the file
      was written but the log line was lost in a crash: append the missing changelog line, skip.
   b. **Conflict?** Current hash ≠ `base_hash` (`null` = file must not exist) → the **whole
      group** is rejected `conflict`; nothing in it is written.
3. For each surviving op: write `<file>.tmp-<uuid>`, `fsync`, `os.replace` onto the target (archive
   = `os.replace` into `_archive/`), then immediately append its changelog line.
4. If anything was applied, regenerate `MEMORY.md` once at the end (atomic); release the lock.

`index_sync` is not an op in a group: `core.writer.sync_index` re-derives `MEMORY.md` under the
lock when it drifted and logs one `index_sync` entry (never undoable). Memory slugs are checked
(`^[a-z0-9]+(-[a-z0-9]+)*$`, ≤ 64) before any path is built, so no op can reach outside `memory/`.

Step 2a makes the activity idempotent: Temporal may retry an activity that actually succeeded,
and a crash between a file write and its log line is detected by content, not reported as a
conflict. Step 2 checks all ops of a group before step 3 writes any of them.

### 6.5 Failure behaviour

- LLM call: retry policy 8 attempts, exponential backoff capped at 1 min, and a rate limit's
  Retry-After replaces the backoff for that attempt (§10.3); vendor 4xx (bad request, auth, spend
  limit, empty balance — the exact classes are in §10.3) is non-retryable and fails the run with
  the vendor's message in `error`.
- Reaching `max_steps` without a final reply: run completes with `status: failed`,
  `error: "max_steps reached"`; write-back is skipped (nothing trustworthy to extract).
- `extract_writeback` failure: run still `completed` with an answer; `writeback` records
  `{applied: [], rejected: [], error: "..."}` — a failed extraction is never shown as "nothing
  to remember" (D-08).

## 7. Feature B — scheduled memory cleanup

### 7.1 Schedule

A Temporal Schedule `memory-cleanup-weekly` starts `MemoryCleanupWorkflow` every Sunday 03:00
`Pacific/Auckland` (`CAIRN_CLEANUP_CRON`, `CAIRN_TZ`). Overlap policy `SKIP`; catch-up window 1
day. `cairn schedule ensure` creates or updates it idempotently; the worker calls the same function
at startup. Workflows cannot read env, so `ensure` puts the current settings into the schedule
action's input (`CleanupInput { review_timeout, stale_days, dup_threshold, dup_body_threshold,
memory_index_budget, auto_apply_mechanical, tz }`) and updates them when settings change. The
schedule starts workflow id `cleanup`, to which Temporal appends the start time
(`cleanup-2026-10-25T03:00:00Z`). Likewise `POST /api/runs`
passes `max_steps` and budgets in `RunInput`, and `POST /api/cases/{id}/checks` fills `CheckInput`.

`POST /api/cleanup/run` first describes the schedule: if `info.running_actions` is non-empty it
returns **409** `cleanup_in_progress` with that workflow id (a trigger would be silently dropped by
`SKIP`); otherwise it calls `schedule.trigger()` and returns 202. Before the worker or `ensure`
has created the schedule it returns **503** `schedule_missing`.

`SKIP` gives single-flight: a cleanup still waiting for review blocks the next one instead of
stacking two proposals over the same files.

### 7.2 Checks (code decides)

`core.lint.lint_home(home, usage, today)` returns findings; each finding may carry a proposed op.

| Check | Severity | Proposed op | Auto-apply |
| --- | --- | --- | --- |
| memory file not in index / index line without file | warn | `index_sync` | yes (mechanical) |
| frontmatter invalid (§4.1 rules) | error | none — a person fixes it | — |
| index over budget (§4.2) | error | none | — |
| SKILL.md invalid, skill name collision across sources, or an unparseable `fact-categories.md` / `checklist.yaml` (§4.3) | error | none | — |
| stale: `last_read` older than `CAIRN_STALE_DAYS` (90) or never read and `created` older than 90 days; and `reads < 2`; and type ≠ `user` | info | `archive` | no |
| near-duplicates: description similarity ≥ 0.82 **or** body similarity ≥ 0.70 | info | cluster → `merge` (§7.3) | no |

Similarity = `rapidfuzz.fuzz.token_set_ratio / 100` on text lower-cased, split on `[a-z0-9:]+`,
stop-words removed. Thresholds are config (`CAIRN_DUP_THRESHOLD`, `CAIRN_DUP_BODY_THRESHOLD`).

Measured on the sample home (`workspace/`, 2026-10-24, rapidfuzz, with the stop-word list
`a an the of to and or for in on is are be by with it its as at so first then before after them they`):
the planted paraphrase pair `conflicts-as-questions` / `neutral-wording-for-discrepancies` scores
description 0.52, body 0.75 — caught by the body check only; across all unrelated pairs the
highest scores are description 0.43 (`adviser-wants-english-findings` /
`neutral-wording-for-discrepancies`) and body 0.53 (`conflicts-as-questions` / `pilot-scope`).
The planted stale memory is `intake-form-v1-dates` (reference, 1 read, last read 2026-04-02).
Tests should assert the pair's exact scores and that exactly one duplicate cluster and one stale
memory are found, not hard-code the unrelated maxima. Note what this shows: a paraphrased
duplicate is invisible to the description check, so the write-back `duplicate` rule (§6.3,
description only) will let some through — cleanup is the backstop, by design.

### 7.3 Merge proposals (model drafts)

For each duplicate cluster (max 5 clusters per run), role `memory.consolidate` gets the cluster's
files and returns:

```
MergeDraft { target_slug, description, body, evidence: [str] }
```

Code accepts a draft only if: `target_slug` is one of the cluster's slugs; it passes §4.1, the
secret scan and the personal-data scan; and every number, date, path, URL and back-ticked
identifier in the merged body occurs in at least one source file (fidelity check). A failed draft
becomes a finding without an op ("could not draft a faithful merge"), never a silently weaker merge.

A merge op = one op group (§6.4): `update` the target with the draft + `archive` the other cluster
members. It has **one** op id in the proposal and one checkbox in the UI; if any member changed
during the review wait, the whole merge is rejected `conflict` (never a half-merge that leaves a
duplicate live).

### 7.4 Review and apply

```
MemoryCleanupWorkflow
  lint            activity -> findings
  apply mechanical ops (index_sync) if CAIRN_AUTO_APPLY_MECHANICAL (default true)
  draft_merges    activity -> merge ops (or findings)
  status = awaiting_review; proposal visible via query get_proposal
  wait_condition(decision received, timeout = CAIRN_REVIEW_TIMEOUT, default 6 days)
     signal submit_review(ReviewDecision { approved_op_ids: [str], reviewer_note?: str })
  timeout -> status = expired; nothing applied
  no op approved ("Reject all") -> status = rejected; nothing applied
  apply approved ops via core.writer (actor "cleanup:<wf_id>") -> status = applied
```

Statuses: `linting`, `drafting`, `awaiting_review`, `applying`, then one of `applied`,
`rejected`, `expired`, `no_changes` (nothing to review: the workflow ends without waiting) or
`failed`. Only the first `submit_review` while `awaiting_review` counts. A merge draft that fails
(vendor error or a refused draft) becomes a `merge_not_drafted` finding. An applied change that the
writer rejects (`conflict`) is listed in the outcome with the writer's reason; the rest still apply.
The fidelity check matches facts as whole tokens: `14` does not occur in `2026-07-14`.
The workflow keeps its status, expiry and change count in its memo, so `GET /api/cleanup` lists
cleanups from Temporal visibility alone, without querying each workflow (which needs a worker).

- Every op shows a before/after diff in the proposal (`before` = current text, `after` = proposed
  text or "moved to _archive/").
- Each op carries the base hash taken at lint time; an op whose file changed during the review
  wait is rejected `conflict` at apply time and reported, not forced.
- Archive = move to `memory/_archive/<slug>.md` (+ changelog). Restore = move back. No hard delete
  anywhere in v1.
- Default review timeout (6 days) is shorter than the schedule period (7 days), so an unanswered
  proposal expires before the next run.

## 8. Feature C — case checks

Two check kinds over one case: `consistency` and `presubmission`. Each is a fixed sequence of
steps in `CaseCheckWorkflow`; the model drafts inside a step, code decides what is accepted and
guarantees that every document, page and checklist item is accounted for (D-13).

### 8.1 Flow

```
POST /api/cases/{case_id}/checks {kind, checklist?}
  -> start CaseCheckWorkflow(CheckInput)       (workflow id = "check-<check_id>")
       load_check_spec      activity -> skill body + fact categories | checklist items (by code)
       ingest               activity per pending document (bounded concurrency)
                                         -> page files (§4.8); doc status ingested|failed
       consistency:
         extract_facts      activity per document part (map; role case.extract_facts)
                                         -> facts validated against page text (§8.3)
         compare            activity (code baseline + role case.compare_facts) -> conflicts (§8.4)
       presubmission:
         check_items        activity per item batch (role case.check_item) -> item results (§8.5)
       write_result         activity -> checks/<check_id>.json (§4.9)
  query get_state  -> CheckState (step, progress counts, coverage so far, error?)
```

`CheckInput { check_id, case_id, kind, checklist_skill?, map_budget, case_context_budget,
min_page_chars, concurrency, item_batch_size }` — filled by the API from settings (workflows
never read env). Activities that call a model bound their own concurrency to `concurrency`
(default 4). All ids are generated by the API before start.

### 8.2 Ingest

- Idempotent by `sha256`: a document whose page files already carry its `source_sha256` is skipped.
- PDF: each page's text layer via `pypdfium2`; a page under `min_page_chars` is rendered to PNG
  (144 dpi, or 72 dpi when that would exceed 25 megapixels; a page too large even then is
  `unreadable` without a model call) and sent to `document.transcribe`. PNG/JPEG: one page, transcribed. Text/Markdown: one
  page, `method: text`.
- `document.transcribe` returns `{readable: bool, text, reason?}` (structured). `readable: false`
  → `method: unreadable` with the reason. A vendor failure after retries marks the document
  `failed` with the error; the check continues and the document is reported as not checked.
- Limits (config): ≤ 100 documents and ≤ 500 pages per case, ≤ 20 MB per file; over a limit is
  rejected at upload (413 `case_too_large`), never truncated.

### 8.3 Consistency: extract facts (map)

- Unit = one document. If its pages' estimated tokens exceed `map_budget` (default 100,000), it is
  split into consecutive page groups under the budget; every page is in exactly one group. Size the
  output cap for the facts expected, not the input (map-reduce guide §8): a `max_tokens` stop is an
  error for that unit, retried once with half the pages, then reported as a failure.
- Role `case.extract_facts` gets the skill body, the categories, and the pages with their numbers;
  returns `{facts: [{category, subject, qualifier?, value, normalised, page, quote}]}`.
- Code accepts a fact only if: `category` is in the categories list; `page` is in the unit;
  `quote` occurs in that page's text after whitespace normalisation (case-sensitive); `normalised`
  parses for date/period categories (`YYYY`, `YYYY-MM`, `YYYY-MM-DD`, `<start>/<end>`, `..` for an
  open end). Rejected facts go to `dropped` with a reason and are counted in `coverage`; they are
  never silently discarded.
- The map step only records facts; it never asserts that something is missing (only a step that
  has seen every document may say so).

### 8.4 Consistency: compare (reduce)

1. **Rule baseline (code).** Group accepted facts by `(category, subject, qualifier)`, where
   `qualifier` (e.g. employer name) is matched by `token_set_ratio ≥ 0.90` after normalisation.
   Within a group, two facts from different documents conflict when their normalised values differ
   for date/period categories — compared at the coarser of the two precisions, so `2022-03` and
   `2022-03-14` agree — or differ after case/whitespace normalisation for text categories, where
   one value whose words appear in order inside the other is the same value with more detail
   (`Maintenance Engineer` agrees with `Maintenance Engineer, permanent full-time`); the model
   pass still judges text values. The extraction prompt (v2) asks for the bare value in text
   categories, so added detail rarely reaches this rule.
   **Overlapping places.** In a one-place-at-a-time category (`address.period`; jobs, trips and
   family members may overlap), two groups for the same subject whose qualifiers (addresses)
   differ conflict when facts from different documents have overlapping periods — strictly, at
   the coarser precision, so moving out and in within one month only touches (D-20). The
   template wording names each address next to its value.
2. **Model pass.** Role `case.compare_facts` gets the accepted facts (ids, values, document
   names — no page text) and the skill body; returns `{conflicts: [{fact_ids, summary, question}]}`.
   Code accepts one only if every id exists, the facts come from ≥ 2 documents, and they share a
   category; for date/period categories the values must actually differ under rule 1's comparison.
3. **Union.** Model proposals with the same fact-id set count once. Every model proposal whose
   facts are a subset of a rule conflict's facts merges into it (the first lends its wording);
   the rest stand alone. `origin` lists `rule`, `model` or both.
   A rule-only conflict gets a template question ("<doc A> (page n) gives <value A>; <doc B>
   (page m) gives <value B>. Which is correct?", `drafted_by: template`).
4. **Wording guard.** A model question or summary containing any of `fraud|forged|fake|false|
   falsif|lie|liar|fabricat|incorrect|wrong` (case-insensitive, word-start) is replaced by the
   template question; the replacement is counted in the result.

The reduce input is structured facts, not text, so it fits one call for any case within the
limits of §8.2; if the estimate exceeds `case_context_budget`, the model pass is skipped with
`error` recorded on the check, and the rule baseline still runs — the result says so.

### 8.5 Pre-submission: check items

- The adviser picks a `presubmission-*` skill; code loads its `checklist.yaml` (§4.3). The
  workflow fails before any model call if it does not parse.
- Context: all ingested page texts of the case, each labelled with document name and page, as a
  shared prefix (cached across item batches). If its estimate exceeds `case_context_budget`
  (default 150,000 tokens) the check fails with `case_too_large_for_v1` — no silent truncation, no
  partial reading. (Retrieval per item is an open item, §17.)
- Role `case.check_item` gets a batch of ≤ `item_batch_size` (5) items and returns
  `{results: [{item_id, status, finding, citations: [{doc_id, page, quote}]}]}`.
- Code rules, applied per item:
  - every checklist item gets exactly one result; an item missing from the reply → `unable`,
    finding "not evaluated", `downgraded: "missing"`;
  - a citation whose quote is not on the cited page is dropped (to `dropped`);
  - `checked` with no valid citation → `pending`, `downgraded: "no_valid_citation"`;
  - an item id not in the checklist is dropped.
- Unreadable pages and failed documents become `gaps` (§4.9), listed with the items in the same
  review list the adviser works through.
- The result is "clean" only if every item is `checked` and there are no unreadable pages or
  failed documents. The UI shows the three counts, never a single pass/fail badge.

### 8.6 Adviser review and sign-off

- Each finding (conflict or item) gets review actions `confirmed` (needs follow-up), `dismissed`
  (needs a note), `resolved`, `reopened`, appended to `_audit.jsonl` (§4.10). Results themselves
  are immutable; re-running a check after new documents arrive creates a new `check_id`.
- Sign-off rule as in §4.10. The UI shows who signed off and when on the check.
- Memory from review: not in v1. Dismissal notes are the raw material for a later write-back
  (e.g. "a different date format is not a conflict"), §17.

### 8.7 Failure behaviour

- An activity failure after retries on one document marks that document failed; the check
  completes with `documents_failed > 0` and the document listed as not checked.
- A failure in `compare` (model pass) keeps the rule baseline and records the error (§8.4).
- A failure in `check_items` for a batch marks those items `unable`, `downgraded: "call_failed"`.
- `load_check_spec` failure, the data-class gate (§10.4) or `case_too_large_for_v1` fails the
  whole check: the result is written with `status: failed`, the reason in `error` and no findings
  at all (never a partial list that could read as complete).

### 8.8 INZ letter reply (`kind: letter`)

A third check kind in `CaseCheckWorkflow` (D-21): ingest, citations, gaps, review, audit and
sign-off are the same as §8.1–§8.7.

1. **The letter.** Uploaded with `source: inz` (§4.7). `POST /checks {kind: letter,
   letter_doc_id}` is refused with 422 `letter_invalid` unless that document is an INZ letter in
   the case. Its scope is the client's documents plus that letter; every pending document in it
   is ingested. A letter that is not ingested in full (failed,
   unreadable page) fails the check with `letter_unreadable`: no partial list of concerns.
2. **Passages.** Code splits the letter's pages into numbered passages `P1…`: one per line, a
   wrapped sentence joined to its start (the line does not end a sentence and the next starts in
   lower case or follows a line of 70+ characters), a list item (`1.`, `(a)`, `-`) always starting
   a passage, a blank line always ending one, never across pages.
3. **Read** (role `case.read_letter`, one call): `{deadline: {date, quote, page} | null,
   concerns: [{summary, passages, quote, page}], context_passages}`. Code rules:
   - a concern whose passages are unknown, or whose quote is not on its page, is dropped (to
     `dropped`) and its passages count as not accounted for;
   - every passage in no accepted concern and not in `context_passages` becomes an
     `unaccounted` finding (`u1…`) with its text: a paragraph the model skipped is reviewed,
     never lost;
   - the deadline is `verified` only when the quote is on its page and a full date in the quote
     (`7 November 2026`, `07/11/2026` day first, `2026-11-07`) equals `date`; otherwise
     `unverified` (a period such as "within 10 working days" keeps no `due`); no deadline is
     `missing`. It is always finding `d1`: the adviser confirms the date;
   - the wording guard (§8.4) replaces a summary with "INZ raises a concern in P…".
4. **Match** (role `case.match_evidence`, concerns in batches of `item_batch_size`): the case's
   pages except INZ letters as a cached prefix (over `case_context_budget` fails the check with
   `case_too_large_for_v1`), plus the conflicts (id, summary) of the latest completed consistency
   check, if any (`related_check_id`). Reply per concern `{concern_id, status, finding,
   citations, client_request?, conflict_ids}`. The prompt (v2) asks for `client_request` written
   to the client (it goes straight into the client email) and treats a document that only
   mentions a missing item (a cover letter listing it) as `no_evidence`, not `partial`. Code rules mirror §8.5: exactly one result per
   concern (none → `unable`, `downgraded: missing`; failed batch → `unable`, `call_failed`);
   citations verified, a quote from the letter is never evidence; `supported`/`partial` without
   a valid citation → `no_evidence`, `downgraded: no_valid_citation`; unknown conflict ids
   dropped; the wording guard replaces a finding with a neutral template and drops a client
   request.
5. **Drafts, by code.** `client_email` lists each concern's `client_request` (empty when none);
   `reply_outline` has one heading per concern with INZ's quote, the evidence status, the
   verified citations and related conflicts, and a placeholder for the adviser's response. Plain
   English text, copied by the adviser; nothing is sent.
6. **Review.** `d1`, every `q*`, every `u*` and every gap need review before sign-off. "Clean"
   means a verified deadline, no unaccounted passage, no gap and every concern `supported`.
7. **Working days.** The check view carries `deadline_working_days`: Monday-to-Friday days from
   tomorrow to `due` in New Zealand time, negative once passed; public holidays are not counted
   out and the UI says so. Reminders and escalation need notifications and adviser identity (§17).

## 9. Cross-tool reuse

### 9.1 By format

Memory files and `SKILL.md` follow the Claude Code / Agent Skills formats (§4). Consequences:

- `workspace/skills/<x>` can be symlinked into `~/.claude/skills/` or `~/.agents/skills/` and works
  there unchanged; the reverse works via `CAIRN_SKILL_PATHS`.
- A Claude Code memory directory can be pointed at as a harness home's `memory/` (copy, not live
  share, in v1: Cairn regenerates `MEMORY.md`, which Claude Code also edits).

### 9.2 By instruction file

The repo and the harness home both use `AGENTS.md` as the canonical, tool-agnostic file; each
`CLAUDE.md` is a one-line `@AGENTS.md` import plus Claude-only notes. Nested `AGENTS.md` files
give coding agents the same progressive disclosure the runtime agent gets: root file small,
detail one directory down.

### 9.3 By code

`core/` has no framework imports, so the CLI exposes it to any tool or git hook:

```
cairn lint     --home PATH [--json]         # exit 1 on any error-severity finding
cairn index    --home PATH [--check]        # regenerate MEMORY.md; --check exits 1 on drift
cairn context  --home PATH --task "..."     # print the L0 prompt + ContextBreakdown
cairn undo     --home PATH CHANGE_ID
cairn schedule ensure
```

## 10. LLM role layer

Follows the role-layer rule: call sites name a role; config maps role → vendor + model + effort.

### 10.1 Vendors

| Vendor | Reaches | Key | Model id form |
| --- | --- | --- | --- |
| `gateway` | Vercel AI Gateway: Claude (`anthropic/*`) and GPT (`openai/*`) models | `AI_GATEWAY_API_KEY` | the gateway's `provider/model` id, exactly as `GET https://ai-gateway.vercel.sh/v1/models` lists it (`anthropic/claude-sonnet-5.5` — a dot, not `claude-sonnet-5-5`) |
| `anthropic` | Anthropic API directly | `ANTHROPIC_API_KEY` | Anthropic's id (`claude-sonnet-5-5`) |
| `llmgw` | the local LLM gateway (`~/Code/AI/llm-gateway`) on the developer's own ChatGPT/Claude subscription — **local dev and demos only** (D-19) | none (`CAIRN_LLMGW_BASE_URL`, loopback only; `CAIRN_LLMGW_TOKEN` when the gateway requires one) | a gateway profile name (`claude-sub`, `gpt-sub`), from `GET <url>/models` |
| `fake` | nothing: replays `tests/fixtures/llm/<scenario>.json` (`CAIRN_FAKE_SCENARIO`; several files colon-separated, read in order) | — | any |
| `azure` | **reserved, not built in v1**: the path for client data once Azure Australia processing is verified (§10.4) | — | — |

The `gateway` vendor speaks each model family's **native protocol** through the gateway, chosen by
the id's prefix (D-12):

| Prefix | Protocol | SDK and base URL |
| --- | --- | --- |
| `anthropic/` | Anthropic Messages | `anthropic` SDK, `base_url=https://ai-gateway.vercel.sh` |
| `openai/` | OpenAI Chat Completions | `openai` SDK, `base_url=https://ai-gateway.vercel.sh/v1` |
| anything else | — | rejected at startup in v1 |

So the gateway and the direct `anthropic` vendor share one Anthropic adapter (only the base URL
and key differ — the Anthropic SDK 2.x sends the key as a bearer token on both), and GPT models are
reachable only through the gateway in v1. SDK retries are off in both adapters: Temporal retries
the activity, guided by the error class (§10.3).

`llmgw` reuses the OpenAI Chat Completions adapter with the configured base URL and a placeholder
key. Its v1 serves text and structured output only (no tools, no images), so only the five text
roles can use it; `agent.main` and `document.transcribe` stay on `gateway`. It ignores `effort`.
Subscription results can differ from the API: re-run on an API vendor before relying on a result.

### 10.2 Roles

`backend/config/roles.toml` (checked in) sets each role's `vendor`, `model`, `effort` and
`max_tokens`. Env overrides it per field: `CAIRN_ROLE_<ROLE>_<FIELD>`, where `<ROLE>` is the role
upper-cased with `.` → `_` (e.g. `CAIRN_ROLE_CASE_EXTRACT_FACTS_MODEL`). `CAIRN_LLM_VENDOR=fake`
forces every role onto the fake vendor.

| Role | Default (`vendor` / `model` / `effort`) | Needs | Why |
| --- | --- | --- | --- |
| `case.extract_facts` | `gateway` / `anthropic/claude-sonnet-5.5` / `medium` | structured output | extraction: recall decides; Haiku-class models drop facts stated as bare conditions |
| `case.compare_facts` | `gateway` / `anthropic/claude-sonnet-5.5` / `medium` | structured output | pairing facts across documents |
| `case.check_item` | `gateway` / `anthropic/claude-sonnet-5.5` / `medium` | structured output | judging an item against cited pages |
| `case.read_letter` | `gateway` / `anthropic/claude-sonnet-5.5` / `medium` | structured output | reading every point of an INZ letter (§8.8) |
| `case.match_evidence` | `gateway` / `anthropic/claude-sonnet-5.5` / `medium` | structured output | matching each concern to cited pages (§8.8) |
| `document.transcribe` | `gateway` / `anthropic/claude-sonnet-5.5` / `low` | structured output, vision | faithful transcription of scanned pages |
| `agent.main` | `gateway` / `anthropic/claude-sonnet-5.5` / `medium` | tool use | tool use over a small context |
| `memory.extract` | `gateway` / `anthropic/claude-sonnet-5.5` / `medium` | structured output | extraction: recall matters; small models drop items |
| `memory.consolidate` | `gateway` / `anthropic/claude-sonnet-5.5` / `low` | structured output | faithful condensation |
| any role in tests | `fake` | — | scripted replies, no network |

Switching a role to GPT is config only, e.g. `CAIRN_ROLE_MEMORY_CONSOLIDATE_MODEL=openai/gpt-5.4-mini`;
switching to the direct API is `…_VENDOR=anthropic` plus `…_MODEL=claude-sonnet-5-5`. No GPT
default is set because no role has been evaluated on a GPT model yet; measure first.

Sonnet 5.5 accepts `effort`; thinking cannot be disabled, so spend is controlled with `effort`
and `max_tokens` (size `max_tokens` for reasoning plus output). GPT-5-family models also reason by
default and bill it as output, so the same sizing rule applies. Verify every configured id with the
live tests before relying on it.

### 10.3 Adapter contract

`llm/client.py` exposes one call, `call(role, messages, tools?, schema?) -> LlmResult`, and hides
the protocol. Messages may carry text and images (page renders for `document.transcribe`).
`LlmResult { text, tool_calls: [{id, name, args}], stop_reason, usage, model, vendor }` with
`stop_reason` normalised to `end | tool_use | max_tokens | refusal`. Each adapter translates:

| Concern | Anthropic Messages | OpenAI Chat Completions |
| --- | --- | --- |
| system prompt | `system` param | first `system` message; omitted, never sent empty (the gateway refuses an empty one) |
| images | `image` content block (base64 PNG) | `image_url` content part (data URL) |
| tools / tool results | `tools`, `tool_use` / `tool_result` blocks | `tools` (function), `tool_calls` / `tool` messages |
| structured output | JSON-schema output format | `response_format` `json_schema`, `strict: true`: every property required, `additionalProperties: false` |
| effort | `output_config.effort` | `reasoning_effort` |
| output cap | `max_tokens` | `max_completion_tokens` (newer models reject `max_tokens`) |
| shared prefix cache | `cache_control` on the case-pages block (§8.5) and on the system block of every `agent.main` step (`cache_system`) | automatic for prefixes ≥ 1,024 tokens |
| stop reason | `end_turn`/`tool_use`/`max_tokens`/`refusal` | `stop`/`tool_calls`/`length`/`content_filter` |

- Only `llm/vendors/anthropic.py` imports the Anthropic SDK and only `llm/vendors/openai.py`
  imports the OpenAI SDK; `llm/vendors/gateway.py` picks between them by prefix and supplies the
  gateway base URL and key. `llm/vendors/fake.py` replays `[{role, match?, reply}]` and fails
  loudly on an unexpected call.
- Structured output, both protocols: send bounded integers as enums, no `minimum`/`maximum` on
  numbers; validate the reply against the Pydantic model locally.
- Every call returns and records `{role, vendor, model, tokens_in, tokens_out, stop_reason}`,
  including failed and truncated calls. A `max_tokens` stop on a structured role is an error, not a
  partial result.
- Error classes (§6.5): non-retryable = 400/401/403/404, gateway 402 (budget exhausted), OpenAI
  429 with code `insufficient_quota` (an empty balance, not a rate limit), and Anthropic's
  "credit balance is too low" 400. Retryable = other 429s, 5xx, timeouts and connection errors.
  A 429's wait (`retry-after-ms`, else `retry-after`, else the gateway's "Retry after Ns" text)
  becomes the activity's `next_retry_delay`, so Temporal waits what the vendor asked; model
  activities retry up to 8 times (the gateway's free tier allows 5 requests per minute per model).
- Startup validation → the worker refuses to start on: a missing key for a configured vendor; a
  `gateway` model id not in `GET https://ai-gateway.vercel.sh/v1/models` or with a prefix other
  than `anthropic/`/`openai/`; a model whose listed `tags` lack what the role needs (the "Needs"
  column: `tool-use`, `structured-output`, `vision`); an unknown id for the direct `anthropic`
  vendor (its models endpoint); an `llmgw` role whose profile is not in `GET <url>/models` or
  that needs `tool-use` or `vision`, or a non-loopback `CAIRN_LLMGW_BASE_URL`; the data-class gate
  (§10.4).

### 10.4 Data-class gate

`CAIRN_DATA_CLASS` = `synthetic` (default) or `client`. It is written into each new case's manifest
(§4.7) and checked in two places:

- **Startup.** With `client`, every role's vendor must be in `CAIRN_CLIENT_DATA_VENDORS`
  (comma-separated, default empty), and `gateway`/`anthropic` are refused in that list in v1 —
  `llmgw` always (a personal subscription, D-19) —
  so a v1 deployment cannot process client data at all until the `azure` vendor exists and its
  Australian processing, logging, backup and abuse-monitoring locations are verified (D-15).
- **Per check.** `load_check_spec` fails the check if the case's `data_class` is `client` and any
  role the check uses is on a vendor outside the allow-list (protects against a config change
  after the case was created).

The gate is config, not code paths: the role layer is unchanged when `azure` is added.

## 11. API (FastAPI, port 4700, prefix `/api`)

| Method & path | Does |
| --- | --- |
| `POST /api/cases` `{label}` | create a case (manifest with `data_class`); returns `{case_id}` |
| `GET /api/cases` | cases with document counts and latest check per kind |
| `GET /api/cases/{case_id}` | manifest: documents with status and per-page method |
| `POST /api/cases/{case_id}/documents` (multipart, one or more files, optional `source=client\|inz`) | store originals, add to manifest as `pending`; 415 `unsupported_type`, 413 `case_too_large` |
| `GET /api/cases/{case_id}/documents/{doc_id}/original` | the uploaded file |
| `GET /api/cases/{case_id}/documents/{doc_id}/pages/{n}` | page text + frontmatter (§4.8) |
| `GET /api/cases/{case_id}/documents/{doc_id}/pages/{n}/render` | a server-side PNG of the page (≤ 25 MP; 422 `not_renderable` otherwise) |
| `GET /api/checklists` | `presubmission-*` skills with visa, version, owner, item count |
| `POST /api/cases/{case_id}/checks` `{kind, checklist_skill?, letter_doc_id?}` (422 `letter_invalid` for a letter check without an INZ letter) | write `checks/<check_id>.start.json`, then start `CaseCheckWorkflow` (id `check-<check_id>`); returns `{check_id}` (202). A start record without a running workflow or result is shown as failed, never as running forever |
| `GET /api/cases/{case_id}/checks` | checks for the case with status and counts |
| `GET /api/cases/{case_id}/checks/{check_id}` | `CheckState` while running; the result (§4.9) + review state once written; `deadline_working_days` for a letter check (§8.8) |
| `POST /api/cases/{case_id}/checks/{check_id}/findings/{finding_id}/review` `{action, note?, adviser}` | append to audit log; 422 `note_required` for `dismissed` without a note |
| `POST /api/cases/{case_id}/checks/{check_id}/signoff` `{adviser}` | append `signed_off`; 409 `signoff_blocked` listing the findings still open |
| `POST /api/runs` `{task, max_steps?}` | start `AgentRunWorkflow`; returns `{run_id}` |
| `GET /api/runs?limit=` | recent runs from Temporal visibility (`WorkflowType="AgentRunWorkflow"`) |
| `GET /api/runs/{run_id}` | `RunState` (query while running; workflow result once closed) |
| `GET /api/context/preview` | `build_context` output without starting a run (L0 does not depend on the task) |
| `GET /api/memory` | index entries + per-memory usage + index budget status |
| `GET /api/memory/{slug}` | file text + parsed frontmatter + changelog entries for it |
| `GET /api/memory/changelog?limit=` | recent changelog entries, newest first |
| `POST /api/memory/changelog/{change_id}/undo` | undo (§4.5); 409 on conflict |
| `GET /api/skills` | L0 skill entries with source path and read-only flag |
| `GET /api/skills/{name}` | SKILL.md body + list of references |
| `GET /api/cleanup` | latest cleanup runs with status |
| `GET /api/cleanup/{workflow_id}` | proposal: findings + ops with diffs |
| `POST /api/cleanup/{workflow_id}/review` | `ReviewDecision`; 202; 409 `not_awaiting_review` unless status is `awaiting_review`; 422 `unknown_op` for an op id not in the proposal |
| `POST /api/cleanup/run` | trigger the schedule now (202); 409 `cleanup_in_progress`, 503 `schedule_missing` (§7.1) |
| `GET /api/health` | API up + Temporal reachable + home and case store readable + `data_class` (503 with reason otherwise) |

- Errors follow one shape `{error: {code, message}}`. A failed upstream (Temporal down) is 503,
  never 200 with an empty list.
- Pydantic models live in `api/schemas.py` and are the OpenAPI source for the frontend client.
- CORS allows only `http://localhost:4710`.

## 12. Frontend (Next.js 15, port 4710)

### 12.1 Pages (App Router)

Primary navigation is **Cases**; everything else sits under **Manage**.

| Route | Shows |
| --- | --- |
| `/` | redirect to `/cases`; health badge in the header (incl. `data_class`, shown as a banner "Synthetic data only") |
| `/cases` | case list: label, document count, latest consistency and pre-submission result counts, signed off or not; "New case" |
| `/cases/[id]` | upload area (drag and drop, multiple files, type/size errors per file); documents with status and per-page method (text / transcribed by model / unreadable); "Run consistency check", "Run pre-submission check" (checklist picker); a second upload area for INZ letters (tagged "INZ letter" in the list) and "Prepare reply" (letter picker); check history |
| `/cases/[id]/checks/[checkId]` | while running: step and progress counts (polls 1 s). Done: coverage bar (documents, pages, transcribed, unreadable, facts dropped) above the findings. Consistency: one row per conflict — the two (or more) values side by side with document, page and quote, the question, origin (rule/model) badge. Pre-submission: items grouped by status (pending, unable, checked) with citations. INZ letter reply: the deadline (date, working days left, whether the quote was verified) to confirm, each concern with INZ's quote and its evidence status, citations, related conflicts and what to ask the client, passages in no concern, then the client email and reply outline with Copy buttons. Clicking a citation opens the page text (and render) beside the finding with the quote highlighted. Per-finding review actions, then sign-off |
| `/manage/runs`, `/manage/runs/[id]` | agent runs: task box; timeline with context breakdown bar (L0 parts vs baseline), steps, answer, write-back result with diff + Undo |
| `/manage/context` | the exact L0 prompt and its breakdown — the progressive-disclosure explainer; the task is never part of L0, it arrives as the first user message |
| `/manage/memory` | memory list grouped by type, reads/last read, index budget meter; detail drawer with file, history, Undo |
| `/manage/skills` | skill catalog by source (local / read-only mounts), with L1/L2 sizes; checklists show their items |
| `/manage/cleanup` | cleanup runs; proposal view with findings, per-op diff, checkboxes, Approve selected / Reject all; countdown to expiry |

### 12.2 UI rules

- Model-produced text is badged "drafted by model"; transcribed pages are badged "transcribed by
  model"; token numbers are labelled exactly "estimated" or "reported by vendor".
- A check result never shows a single pass/fail; it shows the counts and the coverage bar, and
  "unable to check" items are listed as prominently as pending ones.
- No native `alert/confirm/prompt` — use the dialog component (sign-off, dismiss, Undo, Approve).
- Every list has explicit loading, empty and error states (an API error is shown as an error,
  never as an empty list).

### 12.3 Visual direction

Pinned (D-17): **swiss-grid** owns layout, type and palette; **dense-data** contributes local detail
only. From the design KB (`design/directions/swiss-grid.md`, `dense-data.md`):

- Light ground, black ink, 12-column grid with one gutter, 1px rules as the main structure;
  flush-left, ragged-right text — findings and quotes are read at length.
- One accent colour, **not red**: red, green and amber are reserved for semantics (conflict /
  pending, checked, unable) and diff. The accent marks one thing at a time (current step, primary
  action).
- Dense-data detail: tabular numerals right-aligned; ids, hashes, page numbers, dates in
  monospace; 13–14px body in tables; colour only for status.
- Not Inter. Exact accent and typefaces are chosen in the design pass (`/impeccable shape`) and
  recorded in the frontend's `DESIGN.md` from the shipped build.

## 13. Concurrency, security, limits

- One home-wide write lock (§6.4) and one lock per case (§3.2). Reads take no lock; writers use
  atomic replace so readers never see a half-written file.
- Activities that write run on the normal task queue; correctness comes from the locks, base
  hashes and content hashes, not from worker topology, so scaling workers is safe.
- `read_skill_file` resolves the path and rejects anything outside the skill directory, symlinks
  included.
- Uploads: filenames are never used as paths (stored as `<doc_id>.<ext>` from the sniffed type);
  the media type is sniffed from content, not trusted from the client; size and count limits per
  §8.2; PDFs are parsed in the worker, never rendered in the browser from the original — the UI
  shows server-side page renders.
- The case store must not be inside the harness home; run records, memory and logs never include
  page text. Logs carry ids and counts only.
- Secret and personal-data scans on every write to the harness home (write-back, merge, CLI). The
  API never returns env values.
- Temporal payload discipline: page text never enters workflow history — activities read and write
  page files by id and return ids, counts and validated facts/results only; tool results are
  truncated before entering history (§5 budgets); transcripts passed to `extract_writeback` are
  truncated per §6.3.

## 14. Testing and verification

| Layer | Tooling | What it proves |
| --- | --- | --- |
| core unit | pytest, `tmp_path` copies of `tests/fixtures/home` and `tests/fixtures/cases` | formats, index render, budgets (exact token numbers), validation rule per code incl. `personal_data`, writer atomicity/idempotency/conflict, undo, lint findings with exact lists; checklist and fact-category parsing; quote verification (whitespace, case); date/period normalisation and precision-aware comparison; rule-baseline conflicts on the sample facts (exact list); wording guard |
| case fixtures | `tests/fixtures/cases/aewv-sample/` — synthetic text PDFs and images generated by a checked-in script, with planted facts: questionnaire job start `03/2022` vs employer letter `1 June 2022`; tenancy address period ≠ application form; cover letter cites "Appendix 7", which is absent; one image page the fake transcriber marks unreadable; one consistent date pair at different precision (must **not** conflict) | the expected conflicts and item statuses are written down next to the fixture and asserted exactly |
| workflows | `temporalio.testing.WorkflowEnvironment.start_time_skipping()` + real activities + `fake` vendor; cleanup workflows started directly, not via the schedule | Feature C on the sample case: exact conflicts (ids, origin), exact item statuses incl. downgrades, coverage counts, a failed document reported not hidden, data-class gate refusal; Feature A run produces the expected files; Feature B waits, expires after 6 skipped days, applies only approved ops, rejects a whole merge as `conflict` when one member changes mid-wait |
| vendor adapters | pytest; SDK clients given an `httpx.MockTransport` | exact request bodies per protocol (§10.3: images, tools, schema, effort, output cap, cache marker, no empty system message), base URL and key per vendor, `stop_reason` mapping, error class per status/code |
| API | `httpx.AsyncClient` against the app; `WorkflowEnvironment.start_local()` (real dev server) because the time-skipping server lacks Schedules and visibility listing | status codes, error shape, upload limits and type sniffing, review/sign-off rules (422/409), `GET /api/runs` listing, `cleanup/run` 202 vs 409, `schedule ensure` idempotency, 503 when Temporal is down |
| frontend unit | vitest | formatting/diff helpers, token bar math, quote highlighting |
| e2e mocked | Playwright, API mocked via `page.route` | each page's loading/empty/error/success states |
| e2e full | Playwright against `make dev` with `CAIRN_LLM_VENDOR=fake` | upload the sample case → consistency check → the planted conflicts shown with sources → dismiss one with a note → sign-off blocked until all reviewed → sign-off; pre-submission → "Appendix 7" pending; run → write-back → undo; trigger cleanup → approve → memory archived |
| live (marked `live`) | pytest `-m live` | per path — `gateway` × `anthropic/…`, `gateway` × `openai/…`, direct `anthropic` — one tool-use call, one structured call and one image call; plus the sample case's consistency check end to end on the default roles; each **skips with a printed reason** when its key is missing — never passes silently |

Workflow determinism is part of the test: run each workflow test with replay (`Replayer`) over the
produced history.

## 15. Milestones (vertical slices; each ends with `make check` green)

| # | Slice | Done when |
| --- | --- | --- |
| M0 | Scaffold: uv project, Next app, Makefile, ruff/pyright/eslint/tsc/vitest/Playwright configs, fixture home, `GET /api/health`, a health badge | `make check` passes on the empty skeleton; health badge renders against a running API |
| M1 | `core/`: formats, index, context builder + budgets + baseline, writer + changelog + undo, secrets + personal data, similarity, lint; case store (manifest, page files, locks), checklist/fact-category parsing, quote verification, normalisation, rule-baseline compare; synthetic case fixture + generator; CLI `lint/index/context/undo` | core unit tests cover §4–§6.4, §7.2 and §8.3–§8.5 code rules with exact expectations |
| M2 | Feature C backend: role layer + fake vendor, ingest (text layer + transcription via fake), `CaseCheckWorkflow` for both kinds, data-class gate | workflow tests on the sample case assert exact conflicts, item statuses and coverage |
| M3 | Real vendors: Anthropic and OpenAI adapters, `gateway` and `anthropic` vendors (§10), startup validation, live tests | adapter tests pass; live tests pass for each path with its key and skip visibly without one; the sample case runs live end to end |
| M4 | Feature C UI + API: cases, upload, documents/pages, checks, findings review, sign-off; visual direction applied | mocked e2e for those pages; full e2e "upload → check → review → sign-off" passes |
| M5 | Feature A: `AgentRunWorkflow`, write-back validation, runs/context/memory pages with undo | workflow test asserts written files and rejected op codes; full e2e "run → write-back → undo" |
| M6 | Feature B: lint activity, merge drafting + fidelity check, `MemoryCleanupWorkflow`, schedule ensure, cleanup page; `/manage/skills`, read-only skill mounts | time-skipping tests for wait/expire/approve/conflict; full e2e "trigger → approve → archived" |

The `azure` vendor and real client data are not a v1 milestone: they need the verification in
§10.4 first (§17).

## 16. Left to the builder

- Component library (keep it plain; Tailwind is fine). The visual direction is pinned (§12.3).
- Exact prompt wording for the roles, within §5/§6.3/§7.3/§8 constraints. Prompts live in
  `backend/src/cairn/llm/prompts/*.md`, versioned, with the version recorded per call.
- Polling vs SSE for run and check progress (polling is specified; SSE is an allowed upgrade).
- Stop-word list and whitespace normalisation details, as long as the fixture expectations hold.
- The synthetic fixture generator's tooling (e.g. `reportlab` for PDFs, Pillow for images), as a
  dev dependency only.

### 16.1 Demo deployment (D-22)

Where the demo runs is the builder's choice within these rules; the current one is in
`deploy/oracle/` (`bootstrap.md` for setup and operations).

- **One host, one entry.** One VM runs Docker Compose with Caddy in front: `/api/*` goes to the
  API, everything else to the web app, so the browser sees one origin (`NEXT_PUBLIC_API_URL` is
  empty). The API, the web app and the Temporal dev server (SQLite) are not published. Single
  replica by design: worker and API share the harness home and case store through file locks
  (D-01).
- **Two modes; who triggers model calls decides.**
  - *Private (default)*: only the owner uses it. Caddy listens on the VM's loopback
    (`127.0.0.1:8080`, plain HTTP) and the owner reaches it through an SSH tunnel; the only open
    port is SSH, to the owner's IP. The text roles run on the owner's subscription through the
    local LLM gateway on the same VM (D-19): the worker uses host networking so `127.0.0.1:8787`
    is the VM itself, and the gateway requires a bearer token (`CAIRN_LLMGW_TOKEN`) because
    loopback does not stop other processes on the host. Images and tools stay on a small,
    budget-capped gateway key. Selected by
    `COMPOSE_FILE=…:docker-compose.llmgw.yml:docker-compose.private.yml` in the VM's `.env`.
  - *Public*: other people use it. Caddy publishes 80/443 with automatic TLS; every role runs on
    the gateway key, never the local gateway, and the VM holds no subscription login. The web app
    may run on Vercel instead of the VM (D-22 amendment): its pages need a session from its
    sign-in page (`DEMO_USER`, `DEMO_PASSWORD`, `SESSION_SECRET` in the Vercel environment; on
    Vercel a missing one closes the site), the browser sends the same credential to the API as
    basic auth, and the API allows exactly that origin by CORS (`CAIRN_CORS_ORIGIN`); Caddy lets
    that origin's preflights past the gate and names it on its own 401s. Uploads go from the
    browser to the VM, never through Vercel.
  - *Owner-only public*: the public URL (and Vercel frontend) while nobody but the owner has the
    sign-in credential. Then, as in private mode, the text roles may run on the owner's
    subscription through llm-gateway (`docker-compose.llmgw.yml` puts the worker on the VM's
    network); before the credential is shared, the stack goes back to gateway-only roles and the
    VM's Claude login is removed.
- **A gate before anything else.** Until advisers authenticate (§17), one basic-auth credential
  covers pages and API in both modes, and Caddy rate-limits per IP, strictly on the POSTs that
  start model calls (checks, agent runs, cleanup).
- **Synthetic data only.** The data-class gate stays `synthetic`; there are no backups because
  the data is regenerable. The home volume is seeded once from `workspace/` and never
  overwritten by a deploy.
- **Committed code only.** `deploy.sh` ships `git archive HEAD`, builds on the host and runs
  `smoke.sh` (through a tunnel in private mode): anonymous and wrong-password requests get 401,
  `/api/health` reports the deployed commit (`build`, from `CAIRN_BUILD_SHA`), and every port
  that should be closed is closed from outside. `make rehearse` runs both modes locally with the
  same images, the fake vendor and the full e2e suite through Caddy, and `deploy.sh` itself with
  a release that fails its smoke.
- **Only a release that passed replaces the last one.** Images are tagged with their commit; the
  worker is healthy only once its startup validation passed and it polls (`CAIRN_READY_FILE`).
  A release that does not start healthy or fails the smoke is replaced by the previous release's
  images again; a passing one becomes `current` (images tagged `:current`). The last three
  releases keep their images, so rolling back never needs a build on the small VM.

## 17. Open items (not blocking v1)

- **Client data**: the `azure` vendor (Azure OpenAI or Claude in Azure, Australian region), and
  verification of where processing, logs, backups and abuse monitoring happen; client consent
  recorded per case; auth for advisers so sign-off is an authenticated identity.
- Per-item retrieval for pre-submission checks on cases over `case_context_budget`.
- Spouse-visa evidence organisation (hundreds of images, map-reduce over files, photo dates) and
  case briefs — reuse ingest and citations from Feature C.
- INZ letter deadlines: reminders and escalation to a manager (needs notifications and adviser
  identity), and New Zealand public holidays in the working-day count.
- Memory write-back from adviser review notes (e.g. recurring dismissals), through §6.3's
  validation.
- More upload types (DOCX, HEIC, email `.eml`/`.msg`).
- Skill write-back (agent proposes a new skill from repeated work) — same propose/validate/review
  pattern as §7, needs its own fidelity rules.
- Live two-way sharing with a Claude Code memory directory (needs a merge strategy for
  `MEMORY.md`).
- Embedding similarity if lexical duplicates miss real ones in practice — decide from cleanup
  review data, not up front.
