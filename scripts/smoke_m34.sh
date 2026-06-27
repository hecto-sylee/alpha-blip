#!/usr/bin/env bash
# End-to-end smoke test for blip MVP (M3-M4).
# (1) quest candidates(3) -> select(lock)
# (2) dummy webm clip upload 201 -> record save (links clip) -> GET /api/records shows it
# (3) A creates room (6-digit join_code) -> GET /rooms/code/{code} -> B joins ->
#     B shares record (visibility=room) -> A toggles reaction ->
#     GET /rooms/{id} timeline shows record + reaction
set -euo pipefail

BASE="${BASE:-http://localhost:8000}"
TODAY="$(date +%F)"
J() { python3 -c "import sys,json; d=json.load(sys.stdin); print(d$1)"; }

pass() { echo "  ✅ $1"; }
fail() { echo "  ❌ $1"; exit 1; }

guest() { curl -s -X POST "$BASE/api/auth/guest" -H 'Content-Type: application/json' -d "{\"nickname\":\"$1\"}"; }

echo "== setup: guests A & B =="
A=$(guest "초코아빠"); TOKEN_A=$(echo "$A" | J "['auth_token']")
B=$(guest "보리엄마"); TOKEN_B=$(echo "$B" | J "['auth_token']")
pass "A & B created"

echo "== [1] quest candidates(3) -> select(lock) =="
CAND=$(curl -s "$BASE/api/quests/candidates?scope=user" -H "Authorization: Bearer $TOKEN_A")
echo "  candidates raw: $CAND"
N=$(echo "$CAND" | J "[len(['candidates'])]" 2>/dev/null || echo "$CAND" | python3 -c "import sys,json;print(len(json.load(sys.stdin)['candidates']))")
[ "$N" = "3" ] && pass "got 3 candidates" || fail "expected 3 candidates, got $N"
QT=$(echo "$CAND" | python3 -c "import sys,json;print(json.load(sys.stdin)['candidates'][0]['quest_template_id'])")

SEL=$(curl -s -X POST "$BASE/api/quests/select" -H "Authorization: Bearer $TOKEN_A" -H 'Content-Type: application/json' \
  -d "{\"scope\":\"user\",\"scope_id\":\"$(echo "$A" | J "['user_id']")\",\"quest_template_id\":\"$QT\",\"quest_date\":\"$TODAY\"}")
DQ=$(echo "$SEL" | J "['daily_quest_id']"); LOCKED=$(echo "$SEL" | J "['locked']")
[ -n "$DQ" ] && [ "$LOCKED" = "True" ] && pass "selected & locked: $DQ" || fail "select failed: $SEL"

# re-select same day must 409
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/api/quests/select" -H "Authorization: Bearer $TOKEN_A" -H 'Content-Type: application/json' \
  -d "{\"scope\":\"user\",\"scope_id\":\"$(echo "$A" | J "['user_id']")\",\"quest_template_id\":\"$QT\",\"quest_date\":\"$TODAY\"}")
[ "$CODE" = "409" ] && pass "re-select same day -> 409 (lock honored)" || fail "expected 409, got $CODE"

echo "== [2] clip upload 201 -> record save -> GET /records =="
DUMMY=/tmp/blip_dummy.webm
printf '\x1a\x45\xdf\xa3blip-dummy-webm-bytes' > "$DUMMY"
UP=$(curl -s -X POST "$BASE/api/clips/upload" -H "Authorization: Bearer $TOKEN_A" \
  -F "file=@$DUMMY;type=video/webm" -F "duration_ms=2000" -F "order=0")
echo "  upload raw: $UP"
CLIP=$(echo "$UP" | J "['clip_id']")
[ -n "$CLIP" ] && pass "clip uploaded: $CLIP" || fail "clip upload failed"

REC=$(curl -s -X POST "$BASE/api/records" -H "Authorization: Bearer $TOKEN_A" -H 'Content-Type: application/json' \
  -d "{\"visibility\":\"diary\",\"walked_at\":\"$TODAY\",\"duration_minutes\":30,\"distance_meters\":1200,\"text\":\"오늘 산책 좋았다\",\"clip_ids\":[\"$CLIP\"]}")
REC_ID=$(echo "$REC" | J "['record_id']")
[ -n "$REC_ID" ] && pass "record saved: $REC_ID" || fail "record save failed: $REC"

LIST=$(curl -s "$BASE/api/records?from=$TODAY&to=$TODAY" -H "Authorization: Bearer $TOKEN_A")
FOUND=$(echo "$LIST" | python3 -c "import sys,json;d=json.load(sys.stdin);r=[x for x in d['records'] if x['id']=='$REC_ID'];print(len(r[0]['clips']) if r else -1)")
[ "$FOUND" = "1" ] && pass "record in /records with 1 linked clip, daily_quest auto-linked=$(echo "$LIST" | python3 -c "import sys,json;d=json.load(sys.stdin);print([x['daily_quest_id'] for x in d['records'] if x['id']=='$REC_ID'][0])")" || fail "record/clip not listed (clips=$FOUND)"

echo "== [3] room create -> code -> B join -> B shares record -> A reaction -> timeline =="
ROOM=$(curl -s -X POST "$BASE/api/rooms" -H "Authorization: Bearer $TOKEN_A" -H 'Content-Type: application/json' \
  -d '{"name":"동네 산책팟","mode":"walk_friend"}')
ROOM_ID=$(echo "$ROOM" | J "['room_id']"); CODE6=$(echo "$ROOM" | J "['join_code']")
echo "  room raw: $ROOM"
[ ${#CODE6} -eq 6 ] && pass "room created, 6-digit join_code=$CODE6" || fail "join_code not 6 chars: $CODE6"

BYCODE=$(curl -s "$BASE/api/rooms/code/$CODE6" -H "Authorization: Bearer $TOKEN_B" | J "['room_id']")
[ "$BYCODE" = "$ROOM_ID" ] && pass "lookup by code resolves room" || fail "code lookup mismatch: $BYCODE"

JOIN=$(curl -s -X POST "$BASE/api/rooms/$ROOM_ID/join" -H "Authorization: Bearer $TOKEN_B" | J "['status']")
[ "$JOIN" = "joined" ] && pass "B joined room" || fail "join failed: $JOIN"

# B uploads a clip + shares a room record
UPB=$(curl -s -X POST "$BASE/api/clips/upload" -H "Authorization: Bearer $TOKEN_B" \
  -F "file=@$DUMMY;type=video/webm" -F "duration_ms=2000" -F "order=0" | J "['clip_id']")
RECB=$(curl -s -X POST "$BASE/api/records" -H "Authorization: Bearer $TOKEN_B" -H 'Content-Type: application/json' \
  -d "{\"visibility\":\"room\",\"room_id\":\"$ROOM_ID\",\"walked_at\":\"$TODAY\",\"text\":\"방에 공유해요\",\"clip_ids\":[\"$UPB\"]}")
RECB_ID=$(echo "$RECB" | J "['record_id']")
[ -n "$RECB_ID" ] && pass "B shared room record: $RECB_ID" || fail "room record share failed: $RECB"

# A toggles a reaction on B's room record
RX=$(curl -s -X POST "$BASE/api/reactions" -H "Authorization: Bearer $TOKEN_A" -H 'Content-Type: application/json' \
  -d "{\"target_type\":\"record\",\"target_id\":\"$RECB_ID\",\"emoji\":\"🔥\"}" | J "['toggled']")
[ "$RX" = "added" ] && pass "A reaction added (🔥)" || fail "reaction failed: $RX"

DETAIL=$(curl -s "$BASE/api/rooms/$ROOM_ID" -H "Authorization: Bearer $TOKEN_A")
echo "  room detail: $DETAIL"
TL_HAS=$(echo "$DETAIL" | python3 -c "import sys,json;d=json.load(sys.stdin);r=[x for x in d['timeline'] if x['id']=='$RECB_ID'];print('yes' if r else 'no')")
RX_CNT=$(echo "$DETAIL" | python3 -c "import sys,json;d=json.load(sys.stdin);r=[x for x in d['timeline'] if x['id']=='$RECB_ID'];print(sum(a['count'] for a in r[0]['reactions']) if r else 0)")
MEMBERS=$(echo "$DETAIL" | python3 -c "import sys,json;print(len(json.load(sys.stdin)['members']))")
[ "$TL_HAS" = "yes" ] && pass "timeline shows B's record (members=$MEMBERS)" || fail "record missing from timeline"
[ "$RX_CNT" = "1" ] && pass "timeline shows reaction (count=$RX_CNT)" || fail "reaction not in timeline (count=$RX_CNT)"

# toggle off to prove toggle semantics
RX2=$(curl -s -X POST "$BASE/api/reactions" -H "Authorization: Bearer $TOKEN_A" -H 'Content-Type: application/json' \
  -d "{\"target_type\":\"record\",\"target_id\":\"$RECB_ID\",\"emoji\":\"🔥\"}" | J "['toggled']")
[ "$RX2" = "removed" ] && pass "reaction toggle-off works" || fail "toggle-off failed: $RX2"

echo ""
echo "🎉 ALL M3-M4 SMOKE CHECKS PASSED"
