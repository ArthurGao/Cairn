#!/usr/bin/env bash
# One release on the demo VM, run by deploy.sh from that release's own directory (design §16.1):
#   release.sh start <sha>      build its images (tagged <sha>) and start them, waiting for health
#   release.sh rollback <sha>   start an earlier release's images again, without building
#   release.sh promote <sha>    after the smoke passed: tag its images :current (what plain
#                               `docker compose` commands in ~/cairn/current use), point
#                               ~/cairn/current at it, keep three releases with their images
#                               (each can be rolled back to without a build), drop older ones
# CAIRN_DIR (default ~/cairn) holds .env, releases/ and current; PRUNE=0 skips the pruning
# (rehearse.sh, which runs on a laptop with other images).
set -euo pipefail
ACTION="$1" SHA="$2"
CAIRN="${CAIRN_DIR:-$HOME/cairn}"
IMAGES=(cairn-backend cairn-web cairn-caddy)
cd "$CAIRN/releases/$SHA/deploy/oracle"
test -f "$CAIRN/.env" || { echo "$CAIRN/.env is missing (bootstrap.md)" >&2; exit 1; }
ln -sf "$CAIRN/.env" .env
export BUILD_SHA="$SHA"
case "$ACTION" in
  start)
    docker compose build
    docker compose up -d --wait --remove-orphans
    ;;
  rollback)
    docker compose up -d --wait --remove-orphans --no-build
    ;;
  promote)
    for image in "${IMAGES[@]}"; do docker tag "$image:$SHA" "$image:current"; done
    ln -sfn "$CAIRN/releases/$SHA" "$CAIRN/current"
    # shellcheck disable=SC2012  # release directories are commit hashes
    for old in $(ls -1dt "$CAIRN"/releases/*/ | tail -n +4); do
      for image in "${IMAGES[@]}"; do docker image rm "$image:$(basename "$old")" >/dev/null 2>&1 || true; done
      rm -rf "$old"
    done
    if [[ "${PRUNE:-1}" == 1 ]]; then
      # Untagged leftovers go; the build cache stays under 5 GB.
      docker image prune -f >/dev/null
      docker builder prune -f --keep-storage 5GB >/dev/null
    fi
    ;;
  *) echo "usage: $0 start|rollback|promote <sha>" >&2; exit 2 ;;
esac
