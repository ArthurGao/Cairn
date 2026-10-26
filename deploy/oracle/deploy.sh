#!/usr/bin/env bash
# Deploy the committed HEAD to the demo VM, build there (native arm64) and run the smoke.
#   DEMO_USER=… DEMO_PASSWORD=… ./deploy.sh <ssh-target> [public-host]
#   e.g. ./deploy.sh ubuntu@203.0.113.10
# The mode comes from the VM's .env (design §16.1): private (COMPOSE_FILE names
# docker-compose.private.yml) is smoked through an SSH tunnel to the VM's loopback and requires
# every web port closed from outside; public is smoked at https://<public-host> (default
# <ip>.sslip.io). Ports are probed on the ssh target's host (PROBE_HOST overrides it).
# The VM keeps its .env at ~/cairn/.env (bootstrap.md); each release is unpacked into
# ~/cairn/releases/<sha> and run by its own release.sh. If the new release does not start
# healthy or fails the smoke, the previous one is started again; only a release that passed the
# smoke becomes ~/cairn/current. Volumes belong to the Compose project, so demo data survives
# releases and rollbacks. One SSH connection carries every step and the tunnel.
#
# Target `local` is the rehearsal (rehearse.sh release): this machine stands in for the VM under
# $CAIRN_DIR, ships the working tree as release $SHA, smokes http://localhost:8080 without a
# tunnel or port probe, and keeps other images. SMOKE overrides the smoke script.
set -euo pipefail
TARGET="$1"
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(git -C "$HERE" rev-parse --show-toplevel)"
SMOKE="${SMOKE:-$HERE/smoke.sh}"
PROBE="${PROBE_HOST:-${TARGET#*@}}"
HOST="${2:-$PROBE.sslip.io}"
INTERNAL=(4700 4710 7233 8233 8080 8787)
: "${DEMO_USER:?set DEMO_USER}" "${DEMO_PASSWORD:?set DEMO_PASSWORD}"
# The remote side's paths: ~/cairn, or $CAIRN_DIR for the rehearsal (single quotes: expanded there).
# shellcheck disable=SC2016
CAIRN='"${CAIRN_DIR:-$HOME/cairn}"'

if [[ "$TARGET" == local ]]; then
  : "${CAIRN_DIR:?set CAIRN_DIR}" "${SHA:?set SHA}"
  remote() { bash -c "$1"; }
  ship() { git -C "$ROOT" ls-files -co --exclude-standard -z | tar -C "$ROOT" -cf - --null -T -; }
  export CAIRN_DIR PRUNE=0
else
  if [[ -n "$(git -C "$ROOT" status --porcelain)" ]]; then
    echo "the working tree has uncommitted changes; deploy only committed code" >&2
    exit 1
  fi
  SHA="$(git -C "$ROOT" rev-parse HEAD)"
  SOCKET="$(mktemp -u -t cairn-ssh)"
  ssh -f -N -M -S "$SOCKET" "$TARGET"
  trap 'ssh -S "$SOCKET" -O exit "$TARGET" 2>/dev/null' EXIT
  # shellcheck disable=SC2029  # the command is built here on purpose, $CAIRN expands there
  remote() { ssh -S "$SOCKET" "$TARGET" "$1"; }
  ship() { git -C "$ROOT" archive --format=tar HEAD; }
fi
release() { remote "$CAIRN/releases/$2/deploy/oracle/release.sh $1 $2"; }

PREVIOUS="$(remote "p=\$(readlink $CAIRN/current) && basename \"\$p\"" || true)"
echo "deploying $SHA to $TARGET (previous: ${PREVIOUS:-none})"
ship | remote "mkdir -p $CAIRN/releases/$SHA && tar -x -C $CAIRN/releases/$SHA"

roll_back() {
  if [[ -z "$PREVIOUS" || "$PREVIOUS" == "$SHA" ]]; then
    echo "FAILED: $SHA, and there is no earlier release to go back to" >&2
  elif release rollback "$PREVIOUS"; then
    echo "FAILED: $SHA; rolled back to $PREVIOUS" >&2
  else
    echo "FAILED: $SHA, and rolling back to $PREVIOUS failed too; see bootstrap.md" >&2
  fi
  exit 1
}

smoke() {
  local base probe=()
  if [[ "$TARGET" == local ]]; then
    base=http://localhost:8080
  elif remote "grep -q docker-compose.private.yml $CAIRN/.env"; then
    ssh -S "$SOCKET" -O forward -L 18080:127.0.0.1:8080 "$TARGET"
    base=http://localhost:18080 probe=("$PROBE" 80 443 "${INTERNAL[@]}")
  else
    base="https://$HOST" probe=("$PROBE" "${INTERNAL[@]}")
    # The Vercel-hosted frontend's origin, if this public stack serves one.
    CORS_ORIGIN="$(remote "sed -n 's/^CAIRN_CORS_ORIGIN=//p' $CAIRN/.env")"
    export CORS_ORIGIN
  fi
  "$SMOKE" "$base" "$SHA" ${probe[@]+"${probe[@]}"}  # bash 3.2: an empty array under set -u
}

release start "$SHA" || roll_back
smoke || roll_back
release promote "$SHA"
echo "deployed $SHA"
