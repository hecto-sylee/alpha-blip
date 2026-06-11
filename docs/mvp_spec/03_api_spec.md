# API 명세 (FastAPI 구현 기준)

> Base: `/api` · 인증: `Authorization: Bearer {auth_token}` (게스트 토큰)
> S1 매칭/프로필의 상세 바디는 [dev/03_api_spec.md](../dev/03_api_spec.md)를 따른다. 본 문서는 **구현 차이(SQLite/폴링)와 신규 S3 도메인(기록·클립·방·퀘스트·반응)** 을 완전 명세한다.

---

## 공통 규칙

| 항목 | 내용 |
|---|---|
| 인증 | `get_current_user` 의존성. 토큰 없으면 401 |
| 에러 | `{ "error": { "code", "message" } }`, 코드 400/401/403/404/409/500 |
| 시간 | ISO8601 UTC |
| 폴링 | 실시간 대신 클라이언트가 주기 조회 (수신 요청·방 갱신) |
| 이벤트 | 핵심 행동마다 `analytics_events` 1줄 적재 |

---

## Auth (게스트)

### POST /api/auth/guest
닉네임으로 게스트 계정 생성.
```json
// req
{ "nickname": "초코아빠" }
// res 201
{ "user_id": "uuid", "auth_token": "string" }
```
> 클라이언트는 `auth_token`/`user_id`를 localStorage에 저장. 재방문 시 토큰으로 식별.

### GET /api/auth/me
현재 사용자 + 내 반려동물 요약 반환.

---

## Pets (F-02)
`dev/03_api_spec.md` Pets와 동일.
- `POST /api/pets` · `GET /api/pets/{id}` · `PATCH /api/pets/{id}`
- SQLite 구현: `personality_tags` 등 배열은 JSON 직렬화 저장.
- 규칙: 프로필 미등록 사용자는 `POST /api/walks/start` 403 → 등록 유도.

---

## Walks (F-01)

### POST /api/walks/start
```json
{ "pet_id": "uuid", "latitude": 37.5665, "longitude": 126.978 }
// res 201
{ "walk_session_id": "uuid", "started_at": "ISO8601" }
```

### PATCH /api/walks/{id}/location
산책 중 주기 호출. `{ "latitude", "longitude" }` → 200. `lat/lng/location_updated_at` 갱신.

### POST /api/walks/{id}/end
`{ "ended_at", "duration_minutes" }` → 종료. 혼자 산책이면 이후 기록(F-10) 진입의 출처가 된다.

---

## Nearby (F-01)

### GET /api/nearby/dogs
```
query: latitude, longitude, radius_meters(기본 500), size(opt)
```
- 구현: `walk_sessions(status=active, is_location_visible=true)` 중 **Haversine ≤ radius** 필터.
- 응답 `approximate_location` = 실제 좌표 + 무작위 오프셋(`utils/geo.py`). 정확 좌표 미반환.
- 차단 관계(`blocks`)는 양방향 제외.
```json
{ "dogs": [ { "walk_session_id", "pet": {...}, "distance_meters": 230, "approximate_location": { "latitude", "longitude" } } ] }
```

---

## Matches (F-03/04/05)
`dev/03_api_spec.md`의 Match Requests/Sessions/Logs를 그대로 구현. 구현 포인트:

| 엔드포인트 | 구현 규칙 (`services/matching.py`) |
|---|---|
| `POST /api/match-requests` | `expires_at = now + N분`(기본 2분). 차단 관계 불가 |
| `GET /api/match-requests/incoming` | **폴링** 대상. `pending` + 미만료만 |
| `PATCH /api/match-requests/{id}/accept` | 트랜잭션으로 세션 생성, 동일 수신자의 다른 `pending` 자동 `expired` |
| `PATCH /api/match-requests/{id}/reject` · `DELETE .../{id}` | 종료 처리 |
| `POST /api/match-sessions/{id}/end` | 양측 종료 → `match_logs` 생성, `meet_count` 누적 |

> 만료 처리: 별도 스케줄러 없이 **조회 시점에 lazy 만료**(`expires_at < now`면 expired 취급).

---

## Records (F-10)

### POST /api/records
산책 종료 후 기록 저장. 클립은 먼저 업로드(아래)하고 그 id들을 연결하거나, `record` 생성 후 클립을 붙인다.
```json
{
  "walk_session_id": "uuid|null",
  "match_session_id": "uuid|null",
  "daily_quest_id": "uuid|null",
  "visibility": "diary|room",
  "room_id": "uuid|null",          // visibility=room일 때 필수
  "walked_at": "2026-06-11",
  "duration_minutes": 30,
  "distance_meters": 1200,
  "text": "string|null",
  "decoration_json": "string|null",
  "clip_ids": ["uuid", "..."]      // 연결할 업로드된 클립
}
// res 201
{ "record_id": "uuid" }
```
- 규칙: 미디어·텍스트 모두 없어도 저장 가능. `visibility=room`이면 작성자가 해당 방 멤버여야 함(403).
- 저장 시 `daily_quest_id` 자동 연결(그날 퀘스트 있으면).

### GET /api/records?from=&to=
캘린더용. 내 기록 목록(날짜별). `GET /api/records/{id}` 상세.

### PATCH /api/records/{id} · DELETE /api/records/{id}
본인만. 삭제는 연결 클립도 `hidden`.

---

## Clips (F-10) — 2초 영상

### POST /api/clips/upload  `multipart/form-data`
```
fields: file(WebM), record_id(opt), mission_id(opt), duration_ms, order
// res 201
{ "clip_id": "uuid", "file_path": "uploads/..", "stream_url": "/api/clips/{id}/stream" }
```
- 서버: `aiofiles`로 `uploads/{id}.webm` 저장. `duration_ms`는 참고값(클라이언트가 2초 강제).
- `record_id` 없이 먼저 업로드 후 `POST /records`의 `clip_ids`로 묶어도 됨.

### GET /api/clips/{id}/stream
WebM 스트리밍(Range 지원 권장). 비공개 방 클립은 멤버만 접근.

### DELETE /api/clips/{id}
본인 당일 클립만 → `status='hidden'` (공유 로그에서 숨김).

---

## Quests (F-12)

### GET /api/quests/candidates?scope=user|room&scope_id=&mode=
오늘의 퀘스트 후보 3개(랜덤). 이미 그날 선택(lock)됐으면 선택된 퀘스트 반환.
```json
{ "locked": false, "candidates": [ { "quest_template_id", "title", "description", "missions": [{ "id","order","title","hint" }] } ] }
```

### POST /api/quests/select
```json
{ "scope": "user|room", "scope_id": "uuid", "quest_template_id": "uuid", "quest_date": "2026-06-11" }
// res 201
{ "daily_quest_id": "uuid", "locked": true }
```
- 규칙(`services/quest.py`): `(scope, scope_id, quest_date)` 이미 있으면 409(당일 변경 불가). 방(scope=room)은 그날 첫 호출 멤버만 생성, 이후 멤버는 공유된 퀘스트 조회.

### GET /api/quests/today?scope=&scope_id=&date=
오늘의 퀘스트 + 미션 + (선택) 내 미션별 클립 진행 상태.

### (관리) GET /api/admin/quests · PATCH /api/admin/quests/{template_id}
전체 퀘스트 조회/수정(title·description·is_active). MVP 운영용, 인증 단순.

---

## Rooms (F-11)

### POST /api/rooms
```json
{ "name": "동네 산책팟", "mode": "walk_friend|family" }
// res 201
{ "room_id": "uuid", "join_code": "ABC123" }
```
- `services/room.py`: 6자리 코드 발급(중복 회피), 생성자 = owner + 첫 멤버.

### GET /api/rooms/code/{join_code}
코드로 방 조회(참여 전 확인).

### POST /api/rooms/{id}/join
- 인원 초과 409, 이미 멤버면 기존 멤버 반환(중복 참여 방지), `deleted` 방 404.

### GET /api/rooms/{id}
방 상세: 멤버, 오늘의 방 퀘스트(F-12), 공유 기록 타임라인(`records where room_id` + 클립 + 반응 집계).

### POST /api/rooms/{id}/leave
멤버 `left`. 전원 `left` → 방 `deleted`.

### GET /api/rooms (내 방 목록)
참여 중(`joined`) 방 카드 리스트.

---

## Reactions (F-11)

### POST /api/reactions
```json
{ "target_type": "record|clip", "target_id": "uuid", "emoji": "🔥" }
```
- 동일 `(target, user, emoji)` 재호출 시 토글(추가↔취소). 방 공유 대상만 가능.

---

## Privacy (F-09)
`dev/03_api_spec.md` Privacy와 동일:
- `POST /api/privacy/block` · `DELETE /api/privacy/block/{user_id}` · `POST /api/privacy/report`
- 설정값(위치 공유/대략 위치/집 주변 비공개/기록 기본 공개범위)은 `users` 확장 컬럼 또는 별도 `user_settings`로 저장(MVP: 클라 localStorage + 서버 최소 반영).

---

## 엔드포인트 요약

| 도메인 | 주요 엔드포인트 |
|---|---|
| Auth | `POST /auth/guest`, `GET /auth/me` |
| Pets | `POST /pets`, `GET/PATCH /pets/{id}` |
| Walks | `POST /walks/start`, `PATCH /walks/{id}/location`, `POST /walks/{id}/end` |
| Nearby | `GET /nearby/dogs` |
| Matches | `POST /match-requests`, `GET /match-requests/incoming`, `PATCH .../accept|reject`, `DELETE`, `GET /match-sessions/{id}`, `POST /match-sessions/{id}/end|cancel`, `GET /match-logs` |
| Records | `POST /records`, `GET /records`, `GET/PATCH/DELETE /records/{id}` |
| Clips | `POST /clips/upload`, `GET /clips/{id}/stream`, `DELETE /clips/{id}` |
| Quests | `GET /quests/candidates`, `POST /quests/select`, `GET /quests/today`, admin |
| Rooms | `POST /rooms`, `GET /rooms`, `GET /rooms/code/{code}`, `POST /rooms/{id}/join|leave`, `GET /rooms/{id}` |
| Reactions | `POST /reactions` |
| Privacy | `POST /privacy/block`, `DELETE /privacy/block/{id}`, `POST /privacy/report` |
