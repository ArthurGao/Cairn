#!/usr/bin/env bash
# Rehearse the demo stack locally (arm64 Mac = the VM's architecture): the same images and
# Caddyfile with the fixture home and the fake LLM vendor, then smoke.sh and the full e2e suite
# through Caddy.   ./rehearse.sh [public|private]   (design §16.1)
#   public:  https://localhost on 80/443 with Caddy's local CA
#   private: http://localhost:8080 on loopback, worker on host networking (Docker Desktop's host
#            networking stands in for the VM's loopback)
# Removes its own containers, volumes and images; refuses if the ports it needs are taken.
set -euo pipefail
MODE="${1:-public}"
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
FILES=(-f "$HERE/docker-compose.yml")
case "$MODE" in
  public) PORTS=(80 443) CAIRN_HOST=localhost BASE=https://localhost ;;
  private)
    PORTS=(8080 7233) CAIRN_HOST=:80 BASE=http://localhost:8080
    FILES+=(-f "$HERE/docker-compose.private.yml")
    ;;
  *) echo "usage: $0 [public|private]" >&2; exit 2 ;;
esac
for port in "${PORTS[@]}"; do
  if lsof -ti "tcp:$port" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "port $port is in use; stop that process first" >&2
    exit 1
  fi
done
WORK="$(mktemp -d -t cairn-rehearsal)"
DEMO_PASSWORD="$(openssl rand -hex 16)"
BUILD_SHA="rehearsal-$(git -C "$ROOT" rev-parse --short HEAD)"
export DEMO_USER=rehearsal DEMO_PASSWORD BUILD_SHA CAIRN_ENV_FILE="$WORK/.env"
touch "$WORK/.env"
COMPOSE=(docker compose -p "cairn-rehearsal-$MODE" "${FILES[@]}"
  -f "$HERE/docker-compose.rehearsal.yml" --env-file "$WORK/.env")
cleanup() {
  "${COMPOSE[@]}" down -v --remove-orphans >/dev/null 2>&1 || true
  docker image rm "cairn-backend:$BUILD_SHA" "cairn-web:$BUILD_SHA" >/dev/null 2>&1 || true
  rm -rf "$WORK"
}
trap cleanup EXIT
"${COMPOSE[@]}" build
# Hash with the Caddy that will check it.
HASH="$(docker run --rm cairn-caddy:local caddy hash-password --plaintext "$DEMO_PASSWORD")"
cat >"$WORK/.env" <<ENV
CAIRN_HOST=$CAIRN_HOST
DEMO_USER=$DEMO_USER
DEMO_PASSWORD_HASH='$HASH'
CAIRN_DATA_CLASS=synthetic
ENV
"${COMPOSE[@]}" up -d --wait
"$HERE/smoke.sh" "$BASE" "$BUILD_SHA"
cd "$ROOT/frontend"
if ! PLAYWRIGHT_BASE_URL="$BASE" E2E_API_URL="$BASE" \
  E2E_SAMPLE_DIR="$ROOT/backend/tests/fixtures/cases/aewv-sample" \
  npx playwright test --config playwright.full.config.ts; then
  "${COMPOSE[@]}" logs --tail 40 worker api caddy
  exit 1
fi
echo "rehearsal passed ($MODE)"
