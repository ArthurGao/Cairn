#!/usr/bin/env bash
# Rehearse the demo stack locally (arm64 Mac = the VM's architecture): the same images and
# Caddyfile with the fixture home and the fake LLM vendor.   ./rehearse.sh [public|private|release]
# (design §16.1)
#   public:  https://localhost on 80/443 with Caddy's local CA; smoke + full e2e through Caddy
#   private: http://localhost:8080 on loopback, worker on host networking (Docker Desktop's host
#            networking stands in for the VM's loopback); smoke + full e2e through Caddy
#   release: deploy.sh itself, with this machine as the VM: release A deploys; release B starts
#            but fails its smoke, so A must be running again and still be current
# Removes its own containers, volumes and images; refuses if the ports it needs are taken.
set -euo pipefail
MODE="${1:-public}"
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
PROJECT="cairn-rehearsal-$MODE"
case "$MODE" in
  public)
    PORTS=(80 443) CAIRN_HOST=localhost BASE=https://localhost OVERLAY=()
    export CORS_ORIGIN=https://cairn-rehearsal.vercel.app  # as if the frontend were on Vercel
    ;;
  private | release)
    PORTS=(8080 7233) CAIRN_HOST=:80 BASE=http://localhost:8080
    OVERLAY=(docker-compose.private.yml)
    ;;
  *) echo "usage: $0 [public|private|release]" >&2; exit 2 ;;
esac
for port in "${PORTS[@]}"; do
  if lsof -ti "tcp:$port" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "port $port is in use; stop that process first" >&2
    exit 1
  fi
done

WORK="$(mktemp -d -t cairn-rehearsal)"
DEMO_PASSWORD="$(openssl rand -hex 16)"
export DEMO_USER=rehearsal DEMO_PASSWORD CAIRN_ENV_FILE="$WORK/.env"
if [[ "$MODE" == release ]]; then
  A=rehearsal-a B=rehearsal-b TAGS=(rehearsal-a rehearsal-b current)
else
  BUILD_SHA="rehearsal-$(git -C "$ROOT" rev-parse --short HEAD)" TAGS=("$BUILD_SHA")
  export BUILD_SHA
fi
# shellcheck disable=SC2329  # run by the trap
cleanup() {
  (cd "$HERE" && docker compose --env-file "$WORK/.env" down -v --remove-orphans >/dev/null 2>&1) ||
    true
  for image in cairn-backend cairn-web cairn-caddy; do
    for tag in "${TAGS[@]}"; do docker image rm "$image:$tag" >/dev/null 2>&1 || true; done
  done
  rm -rf "$WORK"
}
trap cleanup EXIT
# The stock image of the Caddy version the stack builds on; hashing is the same.
HASH="$(docker run --rm caddy:2.10.2 caddy hash-password --plaintext "$DEMO_PASSWORD")"
FILES=(docker-compose.yml ${OVERLAY[@]+"${OVERLAY[@]}"} docker-compose.rehearsal.yml)
cat >"$WORK/.env" <<ENV
COMPOSE_PROJECT_NAME=$PROJECT
COMPOSE_FILE=$(IFS=:; echo "${FILES[*]}")
CAIRN_HOST=$CAIRN_HOST
DEMO_USER=$DEMO_USER
DEMO_PASSWORD_HASH='$HASH'
CAIRN_DATA_CLASS=synthetic
CAIRN_CORS_ORIGIN=${CORS_ORIGIN:-}
ENV

if [[ "$MODE" == release ]]; then
  export CAIRN_DIR="$WORK"
  current() { basename "$(readlink "$WORK/current")"; }
  SHA="$A" "$HERE/deploy.sh" local
  [[ "$(current)" == "$A" ]] || { echo "current is $(current), want $A" >&2; exit 1; }
  if SHA="$B" SMOKE=false "$HERE/deploy.sh" local; then
    echo "release $B was deployed although its smoke failed" >&2
    exit 1
  fi
  [[ "$(current)" == "$A" ]] || { echo "current is $(current) after the rollback, want $A" >&2; exit 1; }
  "$HERE/smoke.sh" "$BASE" "$A"
  echo "rehearsal passed (release: deploy, failed smoke, rollback to $A)"
  exit 0
fi

# The .env above also selects the project and files (relative to here), as on the VM.
cd "$HERE"
COMPOSE=(docker compose --env-file "$WORK/.env")
"${COMPOSE[@]}" up -d --build --wait
"$HERE/smoke.sh" "$BASE" "$BUILD_SHA"
if ! (cd "$ROOT/frontend" && PLAYWRIGHT_BASE_URL="$BASE" E2E_API_URL="$BASE" \
  E2E_SAMPLE_DIR="$ROOT/backend/tests/fixtures/cases/aewv-sample" \
  npx playwright test --config playwright.full.config.ts); then
  "${COMPOSE[@]}" logs --tail 40 worker api caddy
  exit 1
fi
echo "rehearsal passed ($MODE)"
