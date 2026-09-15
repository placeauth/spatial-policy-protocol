#!/usr/bin/env sh
set -eu

base_url="${SPP_SANDBOX_URL:-http://localhost:8080}"

echo "SPP REFERENCE SANDBOX — experimental / non-normative"
for scenario in admitted degraded denied expired tampered missing-restriction-ack changed-subject; do
  echo "\n== $scenario =="
  curl -fsS -X POST "$base_url/verify" -H 'content-type: application/json' \
    -d "{\"scenario\":\"$scenario\"}"
  echo
done
