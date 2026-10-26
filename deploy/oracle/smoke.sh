#!/usr/bin/env bash
# Post-deploy smoke (deployment playbook §3): the gate holds, the deployed build answers, and the
# listed ports are closed from outside.
#   DEMO_USER=… DEMO_PASSWORD=… ./smoke.sh <base-url> <expected-build-sha> [probe-host port…]
#   public:  ./smoke.sh https://<ip>.sslip.io <sha> <ip> 4700 4710 7233 8233 8080 8787
#   private: ./smoke.sh http://localhost:18080 <sha> <ip> 80 443 4700 4710 7233 8233 8080 8787
# https://localhost (the rehearsal) is Caddy's own local CA, which curl is told to accept.
# CORS_ORIGIN (public mode with a frontend on another origin, e.g. Vercel) adds the CORS checks.
set -euo pipefail
BASE="$1" SHA="$2" PROBE="${3:-}"
PORTS=("${@:4}")
CURL=(curl -sS --max-time 15)
[[ "$BASE" == https://localhost* ]] && CURL+=(-k)
: "${DEMO_USER:?set DEMO_USER}" "${DEMO_PASSWORD:?set DEMO_PASSWORD}"
fail() { echo "FAIL: $*" >&2; exit 1; }
status() { "${CURL[@]}" -o /dev/null -w '%{http_code}' "$@"; }

for path in / /api/health; do
  code=$(status "$BASE$path")
  [[ "$code" == 401 ]] || fail "$path without credentials answered $code, want 401"
done
code=$(status -u "$DEMO_USER:wrong-password" "$BASE/api/health")
[[ "$code" == 401 ]] || fail "a wrong password answered $code, want 401"
echo "ok   the gate refuses anonymous and wrong-password requests"

if [[ -n "${CORS_ORIGIN:-}" ]]; then
  # "<status> <Access-Control-Allow-Origin, - if none, twice if sent twice>" for one request.
  cors() {
    "${CURL[@]}" -o /dev/null -D - -w '%{http_code}\n' "$@" | tr -d '\r' |
      awk -F': ' 'tolower($1)=="access-control-allow-origin"{o=$2; n++} /^[0-9]{3}$/{c=$0}
        END{print c, (n > 1 ? "twice" : (o ? o : "-"))}'
  }
  preflight=(-X OPTIONS -H "Access-Control-Request-Method: GET" -H "Access-Control-Request-Headers: authorization")
  got=$(cors "${preflight[@]}" -H "Origin: $CORS_ORIGIN" "$BASE/api/health")
  [[ "$got" == "200 $CORS_ORIGIN" ]] || fail "a preflight from $CORS_ORIGIN got '$got', want '200 $CORS_ORIGIN'"
  got=$(cors -H "Origin: $CORS_ORIGIN" "$BASE/api/health")
  [[ "$got" == "401 $CORS_ORIGIN" ]] || fail "a 401 to $CORS_ORIGIN got '$got', want it readable"
  got=$(cors -u "$DEMO_USER:$DEMO_PASSWORD" -H "Origin: $CORS_ORIGIN" "$BASE/api/health")
  [[ "$got" == "200 $CORS_ORIGIN" ]] || fail "a signed-in call from $CORS_ORIGIN got '$got'"
  got=$(cors "${preflight[@]}" -H "Origin: https://elsewhere.example" "$BASE/api/health")
  [[ "$got" == "401 -" ]] || fail "a preflight from another origin got '$got', want '401 -'"
  echo "ok   CORS: $CORS_ORIGIN only (its preflights pass the gate, its 401s are readable)"
fi

health=$("${CURL[@]}" -u "$DEMO_USER:$DEMO_PASSWORD" "$BASE/api/health")
want=$(jq -cn --arg sha "$SHA" '{status:"ok", temporal:"ok", data_class:"synthetic", build:$sha}')
got=$(jq -c '{status, temporal, data_class, build}' <<<"$health")
[[ "$got" == "$want" ]] || fail "health is $got, want $want"
echo "ok   /api/health: build $SHA, temporal ok, synthetic data only"

cases=$("${CURL[@]}" -u "$DEMO_USER:$DEMO_PASSWORD" "$BASE/api/cases")
jq -e 'type == "array"' <<<"$cases" >/dev/null || fail "/api/cases did not return a list"
code=$(status -u "$DEMO_USER:$DEMO_PASSWORD" "$BASE/cases")
[[ "$code" == 200 ]] || fail "/cases page answered $code"
echo "ok   case list ($(jq length <<<"$cases") cases) and the cases page"

if [[ -n "$PROBE" ]]; then
  # In parallel: a filtered port only times out, so one by one would take 3 s each.
  open=$(for port in "${PORTS[@]}"; do
    (nc -z -G 3 "$PROBE" "$port" 2>/dev/null && echo "$port") &
  done; wait)
  [[ -z "$open" ]] || fail "reachable on $PROBE: ${open//$'\n'/ }"
  echo "ok   closed on $PROBE: ${PORTS[*]}"
fi
echo "smoke passed"
