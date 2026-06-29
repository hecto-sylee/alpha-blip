#!/usr/bin/env bash
# Smoke test for Achievements (badges).
# Proves: empty grid for a new user, and that distance / streak / friend
# milestones unlock at the right thresholds and surface in `unlocked`.
set -euo pipefail

BASE="${BASE:-http://localhost:8000}"
J() { python3 -c "import sys,json; d=json.load(sys.stdin); print(d$1)"; }
pass() { echo "  ✅ $1"; }
fail() { echo "  ❌ $1"; exit 1; }
guest() { curl -s -X POST "$BASE/api/auth/guest" -H 'Content-Type: application/json' -d "{\"nickname\":\"$1\"}"; }
pet() { curl -s -X POST "$BASE/api/pets" -H "Authorization: Bearer $1" -H 'Content-Type: application/json' -d "{\"name\":\"$2\",\"size\":\"small\"}" | J "['pet_id']"; }
has_code() { python3 -c "import sys,json; d=json.load(sys.stdin); print(any(x['code']=='$1' for x in d.get('unlocked',[])))"; }

echo "== setup: guest A =="
A=$(guest "업적러A"); TOKEN_A=$(echo "$A" | J "['auth_token']"); UA=$(echo "$A" | J "['user_id']")
PA=$(pet "$TOKEN_A" "콩")
pass "A=$UA pet=$PA"

echo "== [1] fresh grid: 0 unlocked, full catalog =="
G=$(curl -s "$BASE/api/achievements" -H "Authorization: Bearer $TOKEN_A")
UC=$(echo "$G" | J "['summary']['unlocked_count']")
TC=$(echo "$G" | J "['summary']['total_count']")
[ "$UC" = "0" ] && pass "unlocked_count=0" || fail "expected 0 unlocked, got $UC"
[ "$TC" -ge "20" ] && pass "catalog has $TC badges" || fail "catalog too small: $TC"

echo "== [2] distance: a 6km record unlocks dist_5k =="
TODAY=$(date +%F)
R=$(curl -s -X POST "$BASE/api/records" -H "Authorization: Bearer $TOKEN_A" -H 'Content-Type: application/json' \
  -d "{\"visibility\":\"diary\",\"walked_at\":\"$TODAY\",\"distance_meters\":6000,\"clip_ids\":[]}")
[ "$(echo "$R" | has_code dist_5k)" = "True" ] && pass "dist_5k unlocked on save" || fail "dist_5k not in unlocked: $R"

echo "== [3] streak: records on 3 consecutive days unlock streak_3 =="
D1=$(date -d 'yesterday' +%F); D2=$(date -d '2 days ago' +%F)
curl -s -X POST "$BASE/api/records" -H "Authorization: Bearer $TOKEN_A" -H 'Content-Type: application/json' \
  -d "{\"visibility\":\"diary\",\"walked_at\":\"$D1\",\"distance_meters\":300,\"clip_ids\":[]}" >/dev/null
R3=$(curl -s -X POST "$BASE/api/records" -H "Authorization: Bearer $TOKEN_A" -H 'Content-Type: application/json' \
  -d "{\"visibility\":\"diary\",\"walked_at\":\"$D2\",\"distance_meters\":300,\"clip_ids\":[]}")
[ "$(echo "$R3" | has_code streak_3)" = "True" ] && pass "streak_3 unlocked at 3 consecutive days" || fail "streak_3 not unlocked: $R3"

echo "== [4] friend: match + end unlocks friend_1 (first meet) =="
B=$(guest "업적러B"); TOKEN_B=$(echo "$B" | J "['auth_token']")
PB=$(pet "$TOKEN_B" "보리")
WA=$(curl -s -X POST "$BASE/api/walks/start" -H "Authorization: Bearer $TOKEN_A" -H 'Content-Type: application/json' -d "{\"pet_id\":\"$PA\",\"latitude\":37.5665,\"longitude\":126.9780}" | J "['walk_session_id']")
WB=$(curl -s -X POST "$BASE/api/walks/start" -H "Authorization: Bearer $TOKEN_B" -H 'Content-Type: application/json' -d "{\"pet_id\":\"$PB\",\"latitude\":37.5666,\"longitude\":126.9781}" | J "['walk_session_id']")
REQ=$(curl -s -X POST "$BASE/api/match-requests" -H "Authorization: Bearer $TOKEN_A" -H 'Content-Type: application/json' -d "{\"receiver_walk_session_id\":\"$WB\"}" | J "['match_request_id']")
SESS=$(curl -s -X PATCH "$BASE/api/match-requests/$REQ/accept" -H "Authorization: Bearer $TOKEN_B" | J "['match_session_id']")
END=$(curl -s -X POST "$BASE/api/match-sessions/$SESS/end" -H "Authorization: Bearer $TOKEN_A" -H 'Content-Type: application/json' -d '{"duration_minutes":30,"distance_meters":1500}')
[ "$(echo "$END" | has_code friend_1)" = "True" ] && pass "friend_1 unlocked on match end" || fail "friend_1 not unlocked: $END"

echo "== [5] grid reflects unlocked badges + idempotency =="
G2=$(curl -s "$BASE/api/achievements" -H "Authorization: Bearer $TOKEN_A")
UC2=$(echo "$G2" | J "['summary']['unlocked_count']")
[ "$UC2" -ge "3" ] && pass "grid shows $UC2 unlocked (dist_5k, streak_3, friend_1, …)" || fail "expected >=3 unlocked, got $UC2"
EV=$(curl -s -X POST "$BASE/api/achievements/evaluate" -H "Authorization: Bearer $TOKEN_A" | J "['unlocked']")
[ "$EV" = "[]" ] && pass "re-evaluate is idempotent (no re-unlock)" || fail "re-evaluate returned: $EV"

echo ""
echo "🎉 ALL ACHIEVEMENTS SMOKE CHECKS PASSED"
