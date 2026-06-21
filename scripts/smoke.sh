#!/usr/bin/env bash
# End-to-end smoke test for blip MVP (M0-M2).
# Verifies: (1) SPA shell, (2) guest + pet CRUD, (3) nearby visibility A<-B,
# (4) match request -> accept -> session -> end -> match-log.
set -euo pipefail

BASE="${BASE:-http://localhost:8000}"
J() { python3 -c "import sys,json; d=json.load(sys.stdin); print(d$1)"; }

pass() { echo "  ✅ $1"; }
fail() { echo "  ❌ $1"; exit 1; }

echo "== [1] GET / → SPA shell HTML 200 =="
code=$(curl -s -o /tmp/blip_index.html -w "%{http_code}" "$BASE/")
# SPA-shell marker: the refactored shell mounts into <div id="app"> (title is
# now "blip — 산책·매칭·기록"); assert the shell root, not the old "blip MVP" string.
grep -q 'id="app"' /tmp/blip_index.html || fail "index missing marker"
[ "$code" = "200" ] && pass "SPA shell 200 (marker found)" || fail "got $code"

echo "== [2] Guest signup → pet create/get/update (2xx) =="
A=$(curl -s -X POST "$BASE/api/auth/guest" -H 'Content-Type: application/json' -d '{"nickname":"초코아빠"}')
TOKEN_A=$(echo "$A" | J "['auth_token']")
USER_A=$(echo "$A" | J "['user_id']")
[ -n "$TOKEN_A" ] && pass "guest A: $USER_A" || fail "no token A"

PET_A=$(curl -s -X POST "$BASE/api/pets" -H "Authorization: Bearer $TOKEN_A" -H 'Content-Type: application/json' \
  -d '{"name":"초코","breed":"푸들","age_months":24,"gender":"male","size":"small","is_neutered":true,"personality_tags":["활발함"],"sociality":4,"activity_level":3,"walk_style":"normal","preferred_partner_size":["small","medium"]}' | J "['pet_id']")
[ -n "$PET_A" ] && pass "pet A created: $PET_A" || fail "pet create failed"

GOT=$(curl -s "$BASE/api/pets/$PET_A" -H "Authorization: Bearer $TOKEN_A" | J "['name']")
[ "$GOT" = "초코" ] && pass "pet A get name=$GOT" || fail "pet get mismatch: $GOT"

UPD=$(curl -s -X PATCH "$BASE/api/pets/$PET_A" -H "Authorization: Bearer $TOKEN_A" -H 'Content-Type: application/json' \
  -d '{"caution_notes":"낯선 큰 개 주의","personality_tags":["활발함","겁많음"]}' | J "['caution_notes']")
[ "$UPD" = "낯선 큰 개 주의" ] && pass "pet A updated notes" || fail "pet update mismatch: $UPD"

echo "== [3] A & B start walks → A's nearby shows B (approximate) =="
B=$(curl -s -X POST "$BASE/api/auth/guest" -H 'Content-Type: application/json' -d '{"nickname":"보리엄마"}')
TOKEN_B=$(echo "$B" | J "['auth_token']")
USER_B=$(echo "$B" | J "['user_id']")
PET_B=$(curl -s -X POST "$BASE/api/pets" -H "Authorization: Bearer $TOKEN_B" -H 'Content-Type: application/json' \
  -d '{"name":"보리","breed":"비숑","size":"small"}' | J "['pet_id']")
pass "guest B: $USER_B, pet B: $PET_B"

# A at (37.5665, 126.9780); B ~150m away.
WALK_A=$(curl -s -X POST "$BASE/api/walks/start" -H "Authorization: Bearer $TOKEN_A" -H 'Content-Type: application/json' \
  -d "{\"pet_id\":\"$PET_A\",\"latitude\":37.5665,\"longitude\":126.9780}" | J "['walk_session_id']")
WALK_B=$(curl -s -X POST "$BASE/api/walks/start" -H "Authorization: Bearer $TOKEN_B" -H 'Content-Type: application/json' \
  -d "{\"pet_id\":\"$PET_B\",\"latitude\":37.5678,\"longitude\":126.9785}" | J "['walk_session_id']")
pass "walks started A=$WALK_A B=$WALK_B"

NEARBY=$(curl -s "$BASE/api/nearby/dogs?latitude=37.5665&longitude=126.9780&radius_meters=500" -H "Authorization: Bearer $TOKEN_A")
echo "  nearby raw: $NEARBY"
FOUND_WS=$(echo "$NEARBY" | J "['dogs'][0]['walk_session_id']")
DIST=$(echo "$NEARBY" | J "['dogs'][0]['distance_meters']")
ALAT=$(echo "$NEARBY" | J "['dogs'][0]['approximate_location']['latitude']")
[ "$FOUND_WS" = "$WALK_B" ] && pass "A sees B at ~${DIST}m, approx_lat=$ALAT" || fail "B not visible in A's nearby"
# approximate must differ from exact 37.5678
[ "$ALAT" != "37.5678" ] && pass "approximate_location is fuzzed (not exact)" || fail "approx == exact coord"

echo "== [4] match-request A→B → B accept → session → end → match-log =="
REQ=$(curl -s -X POST "$BASE/api/match-requests" -H "Authorization: Bearer $TOKEN_A" -H 'Content-Type: application/json' \
  -d "{\"receiver_walk_session_id\":\"$WALK_B\"}")
REQ_ID=$(echo "$REQ" | J "['match_request_id']")
[ -n "$REQ_ID" ] && pass "match-request created: $REQ_ID" || fail "match-request failed: $REQ"

INC=$(curl -s "$BASE/api/match-requests/incoming" -H "Authorization: Bearer $TOKEN_B")
INC_ID=$(echo "$INC" | J "['requests'][0]['id']")
[ "$INC_ID" = "$REQ_ID" ] && pass "B sees incoming request" || fail "incoming poll mismatch: $INC"

SESS=$(curl -s -X PATCH "$BASE/api/match-requests/$REQ_ID/accept" -H "Authorization: Bearer $TOKEN_B" | J "['match_session_id']")
[ -n "$SESS" ] && pass "B accepted → session $SESS" || fail "accept failed"

SESS_VIEW=$(curl -s "$BASE/api/match-sessions/$SESS" -H "Authorization: Bearer $TOKEN_A" | J "['partner']['nickname']")
[ "$SESS_VIEW" = "보리엄마" ] && pass "A's session partner=$SESS_VIEW" || fail "session view mismatch: $SESS_VIEW"

LOG=$(curl -s -X POST "$BASE/api/match-sessions/$SESS/end" -H "Authorization: Bearer $TOKEN_A" -H 'Content-Type: application/json' \
  -d '{"duration_minutes":35,"distance_meters":1200}' | J "['match_log_id']")
[ -n "$LOG" ] && pass "session ended → match-log $LOG" || fail "end failed"

LOGS=$(curl -s "$BASE/api/match-logs" -H "Authorization: Bearer $TOKEN_B" | J "['logs'][0]['meet_count']")
[ "$LOGS" = "1" ] && pass "B's match-logs has entry (meet_count=$LOGS)" || fail "match-log not listed: $LOGS"

echo ""
echo "🎉 ALL SMOKE CHECKS PASSED"
