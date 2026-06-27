#!/usr/bin/env bash
# Smoke test for M5 Privacy (F-09): block / unblock / report — all 2xx.
# Also proves block hides the blocked user from nearby (two-way exclusion).
set -euo pipefail

BASE="${BASE:-http://localhost:8000}"
J() { python3 -c "import sys,json; d=json.load(sys.stdin); print(d$1)"; }
pass() { echo "  ✅ $1"; }
fail() { echo "  ❌ $1"; exit 1; }
guest() { curl -s -X POST "$BASE/api/auth/guest" -H 'Content-Type: application/json' -d "{\"nickname\":\"$1\"}"; }

echo "== setup: guests A & B =="
A=$(guest "차단러A"); TOKEN_A=$(echo "$A" | J "['auth_token']"); UA=$(echo "$A" | J "['user_id']")
B=$(guest "대상B");   TOKEN_B=$(echo "$B" | J "['auth_token']"); UB=$(echo "$B" | J "['user_id']")
pass "A=$UA B=$UB"

echo "== [1] POST /api/privacy/block (A blocks B) =="
CODE=$(curl -s -o /tmp/blk.json -w "%{http_code}" -X POST "$BASE/api/privacy/block" \
  -H "Authorization: Bearer $TOKEN_A" -H 'Content-Type: application/json' \
  -d "{\"target_user_id\":\"$UB\"}")
echo "  resp($CODE): $(cat /tmp/blk.json)"
[[ "$CODE" =~ ^2 ]] && pass "block -> $CODE" || fail "block returned $CODE"

echo "== [1b] block hides B from A's nearby (two-way exclusion) =="
PA=$(curl -s -X POST "$BASE/api/pets" -H "Authorization: Bearer $TOKEN_A" -H 'Content-Type: application/json' -d '{"name":"A개","size":"small"}' | J "['pet_id']")
PB=$(curl -s -X POST "$BASE/api/pets" -H "Authorization: Bearer $TOKEN_B" -H 'Content-Type: application/json' -d '{"name":"B개","size":"small"}' | J "['pet_id']")
curl -s -X POST "$BASE/api/walks/start" -H "Authorization: Bearer $TOKEN_A" -H 'Content-Type: application/json' -d "{\"pet_id\":\"$PA\",\"latitude\":37.5665,\"longitude\":126.9780}" >/dev/null
curl -s -X POST "$BASE/api/walks/start" -H "Authorization: Bearer $TOKEN_B" -H 'Content-Type: application/json' -d "{\"pet_id\":\"$PB\",\"latitude\":37.5666,\"longitude\":126.9781}" >/dev/null
N=$(curl -s "$BASE/api/nearby/dogs?latitude=37.5665&longitude=126.9780&radius_meters=500" -H "Authorization: Bearer $TOKEN_A" | python3 -c "import sys,json;print(len(json.load(sys.stdin)['dogs']))")
[ "$N" = "0" ] && pass "B excluded from A's nearby while blocked (dogs=0)" || fail "blocked user still visible (dogs=$N)"

echo "== [2] POST /api/privacy/report (A reports B) =="
CODE=$(curl -s -o /tmp/rep.json -w "%{http_code}" -X POST "$BASE/api/privacy/report" \
  -H "Authorization: Bearer $TOKEN_A" -H 'Content-Type: application/json' \
  -d "{\"target_user_id\":\"$UB\",\"reason\":\"부적절\",\"context\":\"산책 중\"}")
echo "  resp($CODE): $(cat /tmp/rep.json)"
[[ "$CODE" =~ ^2 ]] && pass "report -> $CODE (report_id=$(cat /tmp/rep.json | J "['report_id']"))" || fail "report returned $CODE"

echo "== [3] DELETE /api/privacy/block/{user_id} (A unblocks B) =="
CODE=$(curl -s -o /tmp/unblk.json -w "%{http_code}" -X DELETE "$BASE/api/privacy/block/$UB" \
  -H "Authorization: Bearer $TOKEN_A")
echo "  resp($CODE): $(cat /tmp/unblk.json)"
[[ "$CODE" =~ ^2 ]] && pass "unblock -> $CODE" || fail "unblock returned $CODE"

echo "== [3b] after unblock, B reappears in A's nearby =="
N=$(curl -s "$BASE/api/nearby/dogs?latitude=37.5665&longitude=126.9780&radius_meters=500" -H "Authorization: Bearer $TOKEN_A" | python3 -c "import sys,json;print(len(json.load(sys.stdin)['dogs']))")
[ "$N" = "1" ] && pass "B visible again after unblock (dogs=1)" || fail "expected 1 after unblock, got $N"

echo ""
echo "🎉 ALL M5 PRIVACY SMOKE CHECKS PASSED"
