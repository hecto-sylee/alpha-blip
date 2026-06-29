#!/usr/bin/env bash
# Smoke test for Leagues (weekly ranking).
# Proves: points accrue from records, leaderboard fills to a 30-cohort with AI
# fillers, the user appears with a rank/zone, and rollover promotes a top user.
set -euo pipefail

BASE="${BASE:-http://localhost:8000}"
JKEY() { python3 -c "import sys,json; print(json.load(sys.stdin)$1)"; }
pass() { echo "  ✅ $1"; }
fail() { echo "  ❌ $1"; exit 1; }

echo "== setup: guest A =="
A=$(curl -s -X POST "$BASE/api/auth/guest" -H 'Content-Type: application/json' -d '{"nickname":"리그러A"}')
TOKEN=$(echo "$A" | JKEY "['auth_token']")
curl -s -X POST "$BASE/api/pets" -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{"name":"콩","size":"small"}' >/dev/null
pass "guest A ready"

echo "== [1] fresh league: bronze, 30-cohort, me last =="
L=$(curl -s "$BASE/api/leagues/me" -H "Authorization: Bearer $TOKEN")
TIER=$(echo "$L" | JKEY "['tier']")
CO=$(echo "$L" | JKEY "['cohort_size']")
[ "$TIER" = "bronze" ] && pass "tier=bronze" || fail "expected bronze, got $TIER"
[ "$CO" = "30" ] && pass "cohort filled to 30 (AI fillers)" || fail "cohort size $CO != 30"

echo "== [2] earn points: 8 walk records this week =="
TODAY=$(date +%F)
for i in $(seq 1 8); do
  curl -s -X POST "$BASE/api/records" -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
    -d "{\"visibility\":\"diary\",\"walked_at\":\"$TODAY\",\"distance_meters\":500,\"clip_ids\":[]}" >/dev/null
done
L2=$(curl -s "$BASE/api/leagues/me" -H "Authorization: Bearer $TOKEN")
PTS=$(echo "$L2" | JKEY "['my_points']")
RANK=$(echo "$L2" | JKEY "['my_rank']")
[ "$PTS" -ge "80" ] && pass "my_points=$PTS (8×walk)" || fail "expected >=80 pts, got $PTS"
[ "$RANK" -le "10" ] && pass "climbed into promote zone (rank=$RANK)" || fail "expected rank<=10, got $RANK"

echo "== [3] my row is present, flagged is_me =="
ISME=$(echo "$L2" | python3 -c "import sys,json; d=json.load(sys.stdin); print(sum(1 for e in d['entries'] if e['is_me']))")
[ "$ISME" = "1" ] && pass "exactly one is_me row in board" || fail "is_me rows=$ISME"

echo "== [4] rollover promotes top user bronze -> silver =="
RO=$(curl -s -X POST "$BASE/api/leagues/rollover" -H "Authorization: Bearer $TOKEN")
PROMOTED=$(echo "$RO" | JKEY "['promoted']")
YT=$(echo "$RO" | JKEY "['your_tier']")
[ "$PROMOTED" -ge "1" ] && pass "rollover promoted $PROMOTED user(s)" || fail "no promotions: $RO"
[ "$YT" = "silver" ] && pass "your_tier bronze -> silver" || fail "expected silver, got $YT"

echo "== [5] standing persists on next read =="
L3=$(curl -s "$BASE/api/leagues/me" -H "Authorization: Bearer $TOKEN")
T3=$(echo "$L3" | JKEY "['tier']")
[ "$T3" = "silver" ] && pass "league/me now shows silver" || fail "expected silver, got $T3"

echo ""
echo "🎉 ALL LEAGUE SMOKE CHECKS PASSED"
