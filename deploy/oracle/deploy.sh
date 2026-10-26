#!/usr/bin/env bash
# Deploy the committed HEAD to the demo VM, build there (native arm64) and run the smoke.
#   DEMO_USER=… DEMO_PASSWORD=… ./deploy.sh <ssh-target> [public-host]
#   e.g. ./deploy.sh ubuntu@203.0.113.10
# The mode comes from the VM's .env (design §16.1): private (COMPOSE_FILE names
# docker-compose.private.yml) is smoked through an SSH tunnel to the VM's loopback and requires
# every web port closed from outside; public is smoked at https://<public-host> (default
# <ip>.sslip.io). Ports are probed on the ssh target's host (PROBE_HOST overrides it).
# The VM keeps its .env at ~/cairn/.env (bootstrap.md); each release is unpacked into
# ~/cairn/releases/<sha> and the last three are kept. Volumes belong to the Compose project
# `cairn-demo`, so demo data survives releases.
set -euo pipefail
TARGET="$1"
PROBE_HOST="${PROBE_HOST:-${TARGET#*@}}"
HOST="${2:-$PROBE_HOST.sslip.io}"
: "${DEMO_USER:?set DEMO_USER}" "${DEMO_PASSWORD:?set DEMO_PASSWORD}"
ROOT="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
if [[ -n "$(git -C "$ROOT" status --porcelain)" ]]; then
  echo "the working tree has uncommitted changes; deploy only committed code" >&2
  exit 1
fi
SHA="$(git -C "$ROOT" rev-parse HEAD)"
echo "deploying $SHA to $TARGET"
# shellcheck disable=SC2029  # $SHA is meant to expand here, on the client
git -C "$ROOT" archive --format=tar HEAD |
  ssh "$TARGET" "mkdir -p ~/cairn/releases/$SHA && tar -x -C ~/cairn/releases/$SHA"
ssh "$TARGET" bash -s -- "$SHA" <<'REMOTE'
set -euo pipefail
SHA="$1"
cd ~/cairn/releases/"$SHA"/deploy/oracle
test -f ~/cairn/.env || { echo "~/cairn/.env is missing (bootstrap.md)" >&2; exit 1; }
ln -sf ~/cairn/.env .env
BUILD_SHA="$SHA" docker compose up -d --build --wait --remove-orphans
ln -sfn ~/cairn/releases/"$SHA" ~/cairn/current
ls -1dt ~/cairn/releases/*/ | tail -n +4 | xargs -r rm -rf
# Each release tags its own images; drop those no container uses and cap the build cache.
docker image prune -af >/dev/null
docker builder prune -f --keep-storage 5GB >/dev/null
REMOTE
SMOKE="$(dirname "$0")/smoke.sh"
INTERNAL=(4700 4710 7233 8233 8080 8787)
if ssh "$TARGET" 'grep -q docker-compose.private.yml ~/cairn/.env'; then
  SOCKET="$(mktemp -u -t cairn-tunnel)"
  ssh -f -N -M -S "$SOCKET" -o ExitOnForwardFailure=yes -L 18080:127.0.0.1:8080 "$TARGET"
  trap 'ssh -S "$SOCKET" -O exit "$TARGET" 2>/dev/null' EXIT
  "$SMOKE" http://localhost:18080 "$SHA" "$PROBE_HOST" 80 443 "${INTERNAL[@]}"
else
  "$SMOKE" "https://$HOST" "$SHA" "$PROBE_HOST" "${INTERNAL[@]}"
fi
