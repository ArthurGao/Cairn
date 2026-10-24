# frontend/AGENTS.md

Next.js web UI for Cairn. Read the root `AGENTS.md` first; this file adds frontend-only rules.
Pages and what each shows: design §12. API contract: design §11. Visual direction: design §12.3.

## Stack

Next.js 15 (App Router) · React 19 · TypeScript strict · Tailwind CSS · TanStack Query for server
state · `openapi-typescript` + `openapi-fetch` for the typed API client · vitest · Playwright.

## Layout

```
frontend/
  app/
    layout.tsx  page.tsx            # / : redirect to /cases; header health badge + data-class banner
    cases/page.tsx                  # case list
    cases/[id]/page.tsx             # upload, documents and pages, start checks, check history
    cases/[id]/checks/[checkId]/page.tsx   # coverage, findings, citation viewer, review, sign-off
    manage/runs/  manage/context/  manage/memory/  manage/skills/  manage/cleanup/
  components/                       # CoverageBar, FindingRow, CitationViewer, Upload, StatusCounts,
                                    # TokenBar, StepList, OpDiff, ModelBadge, ConfirmDialog, States
  lib/api/schema.d.ts               # GENERATED from backend OpenAPI; never hand-edit
  lib/api/client.ts                 # openapi-fetch client, base URL from NEXT_PUBLIC_API_URL
  lib/format.ts  lib/diff.ts  lib/highlight.ts
  tests/unit/  tests/e2e/  tests/e2e-full/
```

## Commands (from `frontend/`)

```
npm install
npm run dev            # next dev -p 4710
npm run lint           # eslint . (flat config; not `next lint`, deprecated since Next 15.5)
npm run typecheck      # tsc --noEmit
npm run test           # vitest + playwright (mocked API)
npm run e2e:full       # playwright against the real stack (make dev, fake vendor)
npm run api:gen        # fetch http://localhost:4700/openapi.json -> lib/api/schema.d.ts
npm run api:check      # regenerate from backend (python export, no server) and fail on diff
```

`api:check` must not need a running server: it runs `uv run python -m cairn.api.export_openapi`
in `../backend` and compares the output.

## Rules

- All server data goes through the generated client; no hand-written response types.
- Every data view renders four states explicitly: loading, empty, error (with the API's
  `error.message`), success. An error is never rendered as an empty list.
- Polling: `/cases/[id]/checks/[checkId]` and `/manage/runs/[id]` refetch every 1 s while the
  status is running and stop when it is completed or failed.
- A check result is never summarised as pass/fail: show the status counts and the coverage bar;
  "unable to check" items, unreadable pages and failed documents are as prominent as pending ones.
- Every citation is clickable and opens the page (server-side text and render, never the original
  PDF in the browser) with the quote highlighted (`lib/highlight.ts`, whitespace-normalised like
  the backend).
- Badge model-produced text ("drafted by model") and transcribed pages ("transcribed by model");
  label token numbers exactly "estimated" or "reported by vendor", as the API marks them.
- Destructive or state-changing actions (dismiss, sign-off, Undo, Approve, Reject) use
  `ConfirmDialog`; never `window.alert/confirm/prompt`. Dismiss requires a note.
- Show the `data_class` banner ("Synthetic data only") on every page while it is `synthetic`.
- Diffs (`OpDiff`) are line-based, computed in `lib/diff.ts`, unit-tested with exact output.
- Accessible by default: buttons are `<button>`, inputs have labels, focus is visible; the upload
  area works with the keyboard and a file input, not only drag and drop.

## Visual direction

Pinned: **swiss-grid** with **dense-data** detail (design §12.3, D-17). Light ground, 12-column
grid, 1px rules, flush-left text; one non-red accent; red/green/amber only for status and diffs;
tabular numerals; ids, pages, dates and hashes in monospace; not Inter. Hand it to Impeccable as a
pinned direction (KB `design/directions/swiss-grid.md`); the project's own `DESIGN.md` is written
from the shipped build, never copied from a brand file.

## Testing

- Mocked e2e (`tests/e2e/`): `page.route('**/api/**', …)` with fixtures shaped by the generated
  types; cover each page's four states and the main interactions (upload, start check, review a
  finding, sign-off blocked then allowed, start run, undo, approve).
- Full e2e (`tests/e2e-full/`): base URL `http://localhost:4710`, assumes `make dev` with
  `CAIRN_LLM_VENDOR=fake`, a fresh copy of the fixture home and an empty case store; uploads the
  synthetic sample case and asserts the planted conflicts and item statuses by text, then real
  file effects via the API (audit entries after review; after Approve, `GET /api/memory` no longer
  lists the archived slug).
- Assert concrete text and counts, not visibility alone.
