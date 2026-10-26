# AGENTS.md — Cairn

Tool-agnostic instructions for any coding agent (Claude Code, Codex, Cursor, …) working in this
repository. `CLAUDE.md` imports this file; do not duplicate its content there.

## What this is

**Cairn** is a file-driven agent harness for licensed immigration advisers. Its agents do the
groundwork on a case — reading every document, cross-checking facts, checking completeness — and
hand a draft with page-level sources to the adviser, who decides and signs off.

An agent's long-lived knowledge lives in plain Markdown files (a *harness home*): persistent
**memory**, reusable **skills** (visa checklists, fact categories), and **state** written back
after every run. The agent sees only a small index up front and loads detail on demand
(**progressive disclosure**). A scheduled **memory cleanup** keeps the files healthy over months.
Client documents live in a separate **case store**, never in the harness home.

The files use the same formats as Claude Code memory and the Agent Skills `SKILL.md` standard, so
a harness home is readable and usable by other tools unchanged (**cross-tool reuse**).

v1 implements three features end to end — everything else is a seam, not a feature:

- **Feature C — Case checks** (`CaseCheckWorkflow`, the pilot's reason to exist): a **consistency
  check** (facts that conflict across a case's documents, each with both sources), a
  **pre-submission check** (every checklist item checked / pending / unable, with sources) and an
  **INZ letter reply** (a verified deadline, every concern in the letter mapped to the evidence).
  Code guarantees every document and item is covered and verifies every quote; the adviser
  reviews and signs off. Synthetic data only in v1 (data-class gate).
- **Feature A — Agent run with state write-back** (`AgentRunWorkflow`): progressive disclosure while
  the agent works, then validated, reversible write-back of new memories and a run record.
- **Feature B — Scheduled memory cleanup** (`MemoryCleanupWorkflow`): weekly lint and consolidation
  proposals, applied only after a person approves them in the UI.

Full design: [`docs/design.md`](docs/design.md). Decisions and their reasons:
[`docs/decisions.md`](docs/decisions.md). Read the design section for the area you touch before
writing code; do not read the whole file when one section answers the question.

## Repository layout

```
cairn/
  AGENTS.md  CLAUDE.md        # this file; CLAUDE.md = @AGENTS.md + Claude-only notes
  docs/design.md              # the spec (sections numbered; cite them as design §N)
  docs/decisions.md           # D-NN decision records
  backend/                    # Python 3.12, uv, Temporal worker + FastAPI + CLI   -> backend/AGENTS.md
  frontend/                   # Next.js 15 (App Router, TypeScript)                 -> frontend/AGENTS.md
  workspace/                  # sample harness home used in local dev (NOT by tests)
  .cases/                     # dev case store (gitignored; synthetic documents only)
  deploy/oracle/              # demo VM: Compose stack, Caddyfile, deploy/smoke/rehearse scripts (D-22)
  Makefile                    # dev / check / test entry points
```

`workspace/` is data, not code: it is a valid harness home that Claude Code or Codex can also open
directly (it has its own `AGENTS.md` for the *runtime* agent). Never put repo instructions there.

## Commands (run from repo root)

| Command | What |
| --- | --- |
| `cp backend/.env.example backend/.env && cp frontend/.env.example frontend/.env.local` | First-time setup; fill `AI_GATEWAY_API_KEY` in `backend/.env`. Env files are gitignored; only `.env.example` is committed |
| `make dev` | Temporal dev server (7233, UI 8233) + worker + API (4700) + web (4710) |
| `make temporal-up` / `temporal-down` | Temporal dev server in Docker instead (`docker-compose.yml`, same ports, data in a named volume); then `make dev-app`, or `dev-worker` / `dev-api` / `dev-web` one by one. The worker, API and web always run on the host |
| `make check` | Every gate below; must exit 0 before you say a task is done |
| `make test` | backend `pytest` + frontend `vitest` + Playwright (mocked API) |
| `make e2e-full` | Playwright against the real stack with the `fake` LLM vendor |
| `cd backend && uv run cairn lint --home ../workspace` | Lint a harness home (same code the cleanup workflow uses) |
| `make rehearse` | The demo stack locally (same images, fake vendor) + smoke + full e2e through Caddy |
| `DEMO_USER=… DEMO_PASSWORD=… deploy/oracle/deploy.sh ubuntu@<ip>` | Deploy committed HEAD to the demo VM and smoke it; private mode (owner-only, SSH tunnel) by default (design §16.1, `deploy/oracle/bootstrap.md`) |

`make check` = `ruff check` + `ruff format --check` + `pyright` + `pytest` (backend) and
`npm run lint` + `npm run typecheck` + `npm run test` + `npm run api:check` (frontend).

Ports are fixed: API **4700**, web **4710**, Temporal **7233** / UI **8233**. Before starting
anything, check the port is free (`lsof -ti tcp:<port>`); never kill a process you did not start.

## Rules that apply everywhere

1. **Files are the source of truth.** Memory, skills and state live in the harness home as
   Markdown/JSON. Temporal holds workflow progress only. No database in v1 (design §3, D-01).
2. **One core library.** All parsing, indexing, linting, validation and writing lives in
   `backend/src/cairn/core/` (pure Python: no Temporal, no network, no FastAPI). Workflows,
   activities, the API and the CLI call it; none of them re-implement it (D-03).
3. **Code decides; the model drafts.** The LLM proposes memory operations and merges; code
   validates every proposal against fixed rules before anything is written (design §6.3, §7.3).
   Destructive cleanup ops need human approval; nothing is ever hard-deleted (archive instead).
4. **Every model call names a role** (`agent.main`, `memory.extract`, `memory.consolidate`).
   No vendor SDK import or model id outside `backend/src/cairn/llm/` and `backend/config/roles.toml`
   (design §10).
5. **Every write is reversible and logged**: atomic temp-file + rename, under the home lock, with
   a base-hash check, and a `memory/_changelog.jsonl` entry holding before/after (design §6.4).
6. **Progressive disclosure is a budget, not a style.** The always-loaded context has a token
   budget enforced in code and shown in the UI; never add eager loading to make a test pass.
7. **Tests never call a real LLM** unless they are the explicitly marked live tests, which
   *skip visibly* without a key (design §14). The `fake` vendor serves scripted replies.
8. **Tests never touch `workspace/` or `.cases/`.** Copy `backend/tests/fixtures/home/` and
   `backend/tests/fixtures/cases/` into `tmp_path`.
9. **All code-facing text is English** — comments, docstrings, logs, commit messages, docs.
10. **Client data stays in the case store.** Never write page text or a client's details into the
    harness home, run records, logs or test snapshots; never use a real person's documents —
    fixtures are synthetic and generated by a checked-in script (design §3.2, §13, D-14, D-15).
11. **Coverage is code's job.** A check must account for every document, page and checklist item;
    what was not read or judged is reported as such, never as clean (design §8, D-13).

## Definition of done

- `make check` exits 0; paste the tail of its output as evidence.
- New behaviour has a test that was seen failing first (break the line, watch it go red, restore).
- Tests assert concrete values (file contents, op lists, token counts), not mere presence.
- If you changed an API schema: `npm run api:gen` was run and the generated client is committed
  (`npm run api:check` fails on drift).
- If you changed a file format or a workflow's inputs/outputs: update `docs/design.md` in the same
  change and add a `docs/decisions.md` entry if a decision changed.

## Git

Agents do not run `git add`, `git commit`, `git push` or create branches. Show `git status` /
`git diff`, propose a commit message, and wait for the human.

## Where to look next

- Backend work → `backend/AGENTS.md`
- Frontend work → `frontend/AGENTS.md`
- A format question (memory file, SKILL.md, changelog, case manifest, page file, check result) → design §4
- A workflow question → design §8 (Feature C), §6 (Feature A) or §7 (Feature B)
- Anything touching client data or vendors → design §3.2, §10.4 first
