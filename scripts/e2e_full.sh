#!/usr/bin/env bash
# Full e2e (design §14): the real stack on the standard ports with the fake LLM vendor, a fresh
# copy of the fixture home and an empty case store. Refuses to run if a port is taken, and
# stops only the processes it started.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
for port in 4700 4710 7233 8233; do
  if lsof -ti "tcp:$port" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "port $port is in use; stop that process (or make dev) first" >&2
    exit 1
  fi
done
WORK="$(mktemp -d -t cairn-e2e)"
cp -R "$ROOT/backend/tests/fixtures/home" "$WORK/home"
mkdir "$WORK/cases"
export CAIRN_HOME="$WORK/home" CAIRN_CASES_DIR="$WORK/cases" CAIRN_LLM_VENDOR=fake \
  CAIRN_FAKE_SCENARIO="$ROOT/backend/tests/fixtures/llm/aewv_sample.json:$ROOT/backend/tests/fixtures/llm/agent_run.json" \
  CAIRN_TASK_QUEUE=e2e
PIDS=()
cleanup() {
  for pid in "${PIDS[@]}"; do kill "$pid" 2>/dev/null || true; done
  wait 2>/dev/null || true
  rm -rf "$WORK"
}
trap cleanup EXIT
temporal server start-dev --headless --port 7233 --ui-port 8233 >"$WORK/temporal.log" 2>&1 &
PIDS+=($!)
for _ in $(seq 60); do lsof -ti tcp:7233 -sTCP:LISTEN >/dev/null 2>&1 && break; sleep 0.5; done
(cd "$ROOT/backend" && exec uv run python -m cairn.worker) >"$WORK/worker.log" 2>&1 &
PIDS+=($!)
(cd "$ROOT/backend" && exec uv run uvicorn cairn.api.app:create_app --factory --port 4700) >"$WORK/api.log" 2>&1 &
PIDS+=($!)
(cd "$ROOT/frontend" && exec npm run dev) >"$WORK/web.log" 2>&1 &
PIDS+=($!)
curl -sf --retry 60 --retry-connrefused --retry-delay 1 -o /dev/null http://localhost:4700/api/health
curl -sf --retry 90 --retry-connrefused --retry-delay 1 -o /dev/null http://localhost:4710/cases
if ! (cd "$ROOT/frontend" && E2E_SAMPLE_DIR="$ROOT/backend/tests/fixtures/cases/aewv-sample" npx playwright test --config playwright.full.config.ts); then
  echo "--- worker log ---"; tail -40 "$WORK/worker.log"
  echo "--- api log ---"; tail -40 "$WORK/api.log"
  exit 1
fi
