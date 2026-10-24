# backend/AGENTS.md

Python backend: Temporal worker, FastAPI app and CLI, sharing one core library. Read the root
`AGENTS.md` first; this file adds backend-only rules.

## Stack

Python 3.12 · uv · Pydantic v2 · `temporalio` (Python SDK) · FastAPI + uvicorn · `anthropic` SDK
(only in `llm/vendors/anthropic.py`) · `openai` SDK (only in `llm/vendors/openai.py`) — both also
used through Vercel AI Gateway (design §10, D-12) · `pypdfium2` + Pillow (PDF text layer, page
renders) · `python-multipart` (uploads) · `filelock` · `PyYAML` · `rapidfuzz` · `python-ulid` ·
ruff (lint + format, configured in `pyproject.toml`) · pyright (strict for `core/`) · pytest +
pytest-asyncio.

## Layout

```
backend/
  pyproject.toml
  config/roles.toml                 # role -> vendor/model/effort defaults (design §10)
  src/cairn/
    settings.py                     # pydantic-settings; every CAIRN_* env var declared here once
    core/                           # PURE: no temporalio / fastapi / vendor SDK imports
      formats.py                    # parse/serialise memory files, SKILL.md; §4 validation
      index.py                      # render MEMORY.md, skill index, drift check
      context.py                    # L0 prompt builder, ContextBreakdown, baseline (§5)
      tokens.py                     # estimate_tokens = ceil(chars / 3.5)
      writer.py                     # lock + base hash + atomic replace + changelog + undo (§6.4)
      validate.py                   # write-back rule codes (§6.3): plan_writeback, conflict_rejections
      lint.py                       # cleanup checks (§7.2)
      similarity.py  secrets.py  usage.py  models.py   # secrets.py also holds personal-data patterns
      cases/                        # case store (design §3.2, §4.7–§4.10, §8): still pure
        store.py                    # manifest, page files, results, audit log; case lock
        spec.py                     # parse fact-categories.md and checklist.yaml
        citations.py                # quote verification against page text
        facts.py                    # normalisation, precision-aware compare, rule baseline
        items.py                    # pre-submission item rules (downgrades, coverage)
        wording.py                  # wording guard + template questions
    llm/
      roles.py                      # Role enum, config loading, startup validation
      client.py                     # call(role, messages, tools?, schema?) -> LlmResult
      vendors/anthropic.py          # Anthropic Messages adapter (direct API and gateway anthropic/*)
      vendors/openai.py             # OpenAI Chat Completions adapter (gateway openai/*)
      vendors/gateway.py            # picks the adapter by model prefix; gateway base URL + key
      vendors/fake.py
      prompts/agent_main.md  memory_extract.md  memory_consolidate.md
    workflows/case_check.py  workflows/agent_run.py  workflows/memory_cleanup.py
    activities/ingest.py  case_check.py  context.py  llm.py  tools.py  writeback.py  cleanup.py
    worker.py                       # registers workflows/activities, ensures schedule
    api/app.py  api/routes/*.py  api/schemas.py  api/temporal.py
    cli.py                          # `cairn` entry point (design §9.3)
  tests/
    fixtures/home/                  # canonical test harness home (copy to tmp_path, never mutate)
    fixtures/cases/aewv-sample/     # synthetic case + expected.json (planted conflicts, item statuses)
    fixtures/make_cases.py          # generates the synthetic documents; never a real person's
    fixtures/llm/*.json             # fake-vendor scenarios
    unit/  workflows/  api/  live/
```

## Commands (from `backend/`)

```
uv sync                                   # install
uv run ruff check . && uv run ruff format --check .
uv run pyright
uv run pytest                             # excludes -m live
uv run pytest -m live                     # real vendors; each path skips visibly without its key
                                          # (AI_GATEWAY_API_KEY, ANTHROPIC_API_KEY)
uv run python -m cairn.worker             # worker (needs temporal dev server)
uv run uvicorn cairn.api.app:create_app --factory --port 4700 --reload
uv run cairn lint --home ../workspace
```

After moving the project or adding a path dependency: `rm -rf .venv && uv lock && uv sync`
(console-script shebangs are absolute; `uv sync` alone ignores new path deps).

## Temporal rules

- Workflow modules import activities and models inside `with workflow.unsafe.imports_passed_through():`.
- Workflow code: no file/network I/O, no `datetime.now()` (use `workflow.now()`), no `random`/`uuid4`
  (IDs are passed in or made with `workflow.uuid4()`), no threads. Anything else is an activity.
- Use the Pydantic data converter (`temporalio.contrib.pydantic.pydantic_data_converter`) on every
  `Client.connect`, in the worker, API and tests alike — a mismatch shows up as decode errors.
- Every `execute_activity` sets `start_to_close_timeout` and a `RetryPolicy`; vendor 4xx and
  validation errors are raised as `ApplicationError(non_retryable=True)`.
- Activities that write must be idempotent (design §6.4 `op_id`); assume any activity can run twice.
- Keep payloads small: truncate tool results before returning them from the activity. Page text
  never enters workflow history: case activities take and return ids, counts and validated
  facts/results, and read/write page files themselves (design §13).
- Workflows never read settings/env: every tunable (max_steps, budgets, thresholds, review
  timeout) arrives in the workflow input (`RunInput`, `CleanupInput`), filled from `settings.py`
  by the API or by `schedule ensure`.
- The time-skipping test server has no Schedules or visibility listing: test workflows by
  starting them directly; test schedule/listing code with `WorkflowEnvironment.start_local()`.
- Task queue: `cairn`. Workflow ids: `check-<check_id>`, `run-<run_id>`; cleanup ids come from the
  schedule.
- Local server: `temporal server start-dev --db-filename .temporal/dev.db --port 7233 --ui-port 8233`.

## Testing rules

- Unit tests: copy `tests/fixtures/home` (and `tests/fixtures/cases`) to `tmp_path` with a helper
  fixture; assert on file text, exact op lists, exact rule codes and exact token numbers.
- Case-check tests assert against `fixtures/cases/aewv-sample/expected.json`: exact conflict
  fact-id sets and origins, exact item statuses and downgrades, exact coverage counts. A planted
  same-date-different-precision pair must produce **no** conflict.
- Workflow tests: `WorkflowEnvironment.start_time_skipping()`; real activities pointed at the
  tmp home; LLM through the `fake` vendor with a named scenario file. Replay each produced history
  with `Replayer` to prove determinism. (First run downloads the Temporal test server binary.)
- The fake vendor fails the test on any call its scenario does not expect — do not make it lenient.
- Vendor adapter tests give the SDK client an `httpx.MockTransport` and assert the exact request
  body and the parsed `LlmResult`; never patch the adapter itself.
- Mock only at boundaries: the vendor (via `fake`), the clock (via Temporal time skipping or an
  injected `today`), the filesystem (via `tmp_path`). Never mock `core` inside its own tests.
- Live tests (`tests/live/`, marker `live`) call `pytest.skip` with an explicit reason when the key
  is missing; CI prints the skip count.

## Style

- Type everything; `core/` passes pyright strict.
- Pure functions in `core/` take `home: Path` and `today: date` explicitly — no hidden globals,
  no reading env inside `core`.
- Errors: domain errors subclass `CairnError` with a stable `code`; the API maps them to
  `{error: {code, message}}`.
