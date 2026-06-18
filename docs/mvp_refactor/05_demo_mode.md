# 05 · 데모/테스트 모드 — 홈 test 키로 1인 풀플로우 시연

> **목적:** 기기 1대(또는 헤드리스 1세션)에서 실제 상대 없이 **산책 → 매칭 → 기록 → 방 공유**
> 전 과정을 시연/검증할 수 있게 한다. 홈의 test 키를 누르면 **강남 테헤란로 큰길타워** 위치에서
> 임의의 **목업 유저**가 근처에 뜨고, 그 유저와 매칭(자동 수락)되며, 기록 중 **방 공유**로 로그까지 올린다.
>
> **범위 메모:** 이건 순수 리팩토링(R0~R3)이 아니라 **부가 데모/시연 기능**이다. dev/시연용으로 게이트한다.
> "매칭한 유저를 친구 리스트로" 같은 **친구(매칭 이력) 개념은 현재 데이터모델에 없어 이번 범위에서 제외**한다.
> 대신 **목업 유저를 멤버로 포함한 "데모 방"** 이 매칭 ↔ 방 공유를 잇는 다리 역할을 한다
> (매칭한 그 유저와 같은 방에서 로그를 공유 → 친구 리스트 없이도 의도 충족).

---

## 1. 시나리오 (해피 패스)

```
홈 → [🧪 데모 산책] 키
  → POST /api/demo/setup (큰길타워 좌표)
      · 목업 유저(+펫) 생성/재사용
      · 목업 유저의 active WalkSession을 큰길타워 인근(~80m)에 생성
      · 나 + 목업이 멤버인 "데모 방" 보장
  → #/walk 진입 (데모 위치 = 큰길타워로 고정)
  → 지도에 목업 강아지 마커 노출 (GET /nearby/dogs)
  → 마커 탭 → 바텀시트 → [같이 산책하기] (POST /match-requests)
  → (목업은 클라이언트가 없으므로) 서버가 자동 수락 → match_session 생성
  → 대기화면 폴링이 세션 전환 감지 → 매칭 성사 축하 모션 → 세션(SCR-14)
  → [산책 종료] → 기록 에디터(2초 클립 녹화)
  → 공개범위 [방 공유] 선택 → 데모 방 선택 → 저장(POST /records, visibility=room)
  → 방 탭 로그 피드 / 데모 방 타임라인에 방금 로그 노출
```

## 2. 백엔드 (server/)

### 2-1. 목업 식별자 — `User.is_mock`
- `models.User`에 `is_mock: bool = False`(default) 컬럼 추가(소규모).
- 현재 프로젝트는 Alembic 없이 `Base.metadata.create_all()`만 사용한다. **기존 `walk.db`에는
  `create_all`이 신규 컬럼을 추가하지 않으므로**, 구현 시 dev용 경량 스키마 보정(`ALTER TABLE users
  ADD COLUMN is_mock BOOLEAN DEFAULT 0`) 또는 개발 DB reset 중 하나를 선택한다.
- 목업 유저/펫/세션은 일반 레코드와 동일 테이블, `is_mock=True`로만 구분한다.
- 현재 사용자별 목업을 멱등하게 찾기 위해 기존 고유 필드 `auth_token`에 deterministic sentinel을 쓴다.
  예: `auth_token = "demo-mock:{current_user.id}"`, `email = "demo+{current_user.id}@local.invalid"`.
  별도 친구/관계 테이블은 추가하지 않는다.

### 2-2. `POST /api/demo/setup` (인증 필요)
요청: `{ "latitude": float?, "longitude": float? }` — 미지정 시 **큰길타워 기본 좌표** 사용.
동작(멱등 — 재호출 시 같은 목업/방 재사용·세션 갱신):
1. 현재 유저용 목업 유저 1명 보장(`is_mock=True`, deterministic `auth_token`) + 목업 펫.
2. 목업 유저의 **active WalkSession**을 `(lat+δ, lng+δ)`(~80m, radius 500m 내)로 생성/갱신,
   `is_location_visible=True`, `lat/lng` 세팅.
3. 현재 유저 + 목업이 **active 멤버인 "데모 방"** 보장(없으면 생성, mode=`walk_friend`).
4. 응답:
   ```json
   {
     "mock_user_id": "...", "mock_pet": {...},
     "mock_walk_session_id": "...",
     "room_id": "...", "room_join_code": "ABC123",
     "location": { "latitude": 37.5009, "longitude": 127.0398, "label": "강남 테헤란로 큰길타워" }
   }
   ```

### 2-3. 자동 수락 — 목업 세션 대상 매칭은 즉시 수락
- 매칭 요청(`POST /match-requests`)의 **receiver walk session이 목업 유저 소유면 서버가 즉시
  `accept`**(match_session 생성)한다. 구현 위치 후보:
  - `services/matching.create_request()` 내에서 receiver 세션 user의 `is_mock`이면 바로
    `accept_request` 흐름 수행 → 요청은 생성 직후 `accepted` 상태.
- **클라이언트 매칭 플로우는 그대로**: 기존 대기화면이 `GET /match-requests/{id}`를 폴링하다
  `status=accepted` + `match_session_id`를 받으면 세션으로 전환(코드 변경 최소).
- 큰길타워 좌표는 구현 시 확정(초안: `lat 37.5009, lng 127.0398`, 라벨 "강남 테헤란로 큰길타워").

### 2-4. nearby 오염 방지 — 내 데모 목업만 노출
- `GET /nearby/dogs`에서 `WalkSession` 소유자가 `is_mock=True`이면, 그 목업의 `auth_token`이
  `demo-mock:{current_user.id}`인 경우에만 포함한다. 다른 사용자의 데모 목업은 일반 주변 목록에서 제외한다.
- 이 조건으로 "데모 세션은 기기 1대 시연에만 보이고, 일반 nearby는 오염되지 않음"을 보장한다.

### 2-5. 라우터 등록
- `server/api/demo.py` 신설 → `main.py`의 `include_router(prefix="/api")`에 추가.
- 데모 라우터는 dev 전용 의도(운영 비활성 토글 여지). MVP에선 인증만 요구.
- `schemas.py`에 `DemoSetupReq`, `DemoSetupRes`를 추가하거나 라우터 내부 Pydantic 모델로 둔다.

## 3. 프론트엔드 (server/static/)

### 3-1. 홈 test 키 (`screens/home.js`)
- 큰 CTA 아래에 보조 버튼 `#demo-setup` "🧪 데모 산책 (강남 테헤란로)" 추가.
- onclick: `api.post("/demo/setup")`(실제 `/api/demo/setup`) → 응답을 `store`에 데모 컨텍스트로 저장
  (`store.demo = { lat, lng, mockSessionId, roomId }`) → `navigate("/walk")` → 토스트.
- `store.js`에는 `blip_demo_context` localStorage 키와 `setDemo/get demo/clearDemo` 헬퍼를 추가한다.

### 3-2. 데모 위치 고정 (`screens/walk.js`)
- `store.demo`가 있으면 **geolocation 소스를 데모 좌표로 고정**(watchPosition 대신 데모 lat/lng 사용,
  데스크톱/헤드리스에서 GPS 없이 동작). `PATCH /walks/{id}/location`도 데모 좌표로.
- 기존 `store.walkId`가 남아 있으면 데모 시작 전에 정리하거나, `/api/demo/setup` 이후 `/walks/start`가
  현재 사용자 세션을 큰길타워 좌표로 새로 시작하도록 보장한다.
- 나머지(근처 폴링·마커·바텀시트·요청·세션 전환)는 **기존 로직 그대로** — 목업이 nearby로 떠서
  자연스럽게 매칭된다.
- 산책/매칭 종료 시 `store.demo`는 유지(기록 후 방 공유까지 데모 방을 쓰도록). 기록 저장 성공 또는
  명시적 홈 복귀에서 클리어한다.

### 3-3. 방 공유 (`screens/record.js`) — 기존 흐름 재사용
- 친구 리스트 **추가 없음**. 데모 방이 이미 `GET /rooms`에 잡히므로 공개범위 [방 공유] →
  방 선택 `<select>`에 데모 방이 보이고, 저장 시 `visibility=room, room_id=데모방`으로 업로드.
- 데모 컨텍스트면 방 공유를 기본 프리셋으로 설정한다(`visibility="room"`, `roomId=store.demo.roomId`).

## 4. 검증 (스모크 — `scripts/fe_smoke_demo.py` 신설)
헤드리스 1세션(+geolocation 큰길타워 주입, 카메라/마이크 fake)으로:
1. 게스트/펫 준비 → 홈 `#demo-setup` 클릭 → `/api/demo/setup` 200, `#/walk` 진입.
2. 지도에 **목업 마커**(nearby) 노출 단언 → 마커 탭 → 바텀시트 → [같이 산책하기].
3. 요청 후 **자동 수락**으로 세션(SCR-14) 전환 단언(축하 모션/세션 화면).
4. [산책 종료] → 기록 에디터 → 2초 클립 녹화(201) → 공개범위 [방 공유] → 데모 방 선택 → 저장.
5. 방 탭 로그 피드(또는 데모 방 상세)에 방금 로그 노출 단언.
콘솔 에러 0(외부/WebGL 잡음 제외), 각 단계 스크린샷.

## 5. 주의 / 정리
- 목업/데모 방은 `is_mock`·전용 닉네임으로 구분 → 일반 사용자 nearby/방 목록 오염 주의
  (nearby에서 `demo-mock:{current_user.id}` 소유 목업만 노출).
- 데모 좌표·라벨은 한곳(상수)에서 관리. 큰길타워 정확 좌표는 구현 시 확정.
- 이 기능은 R0~R3(리팩토링)와 **독립**. 디자인은 R0 입체 컴포넌트를 그대로 사용.
