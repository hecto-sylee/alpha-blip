# 프론트엔드 SPA 명세 (Vanilla JS)

> 빌드 스텝 없는 모바일형 SPA. 단일 `index.html` + 모듈 JS. FastAPI가 같은 origin에서 서빙.
> 화면 정의는 [mvp_planning/03_screen_definition.md](../mvp_planning/03_screen_definition.md)(SCR-01~32) 기준.

---

## 아키텍처

```
static/
├─ index.html            # 앱 셸: 헤더/탭바/뷰 컨테이너(#app)
├─ css/app.css           # 디자인 토큰은 mvp_planning/04_ui_ux_style.md 참조
└─ js/
   ├─ app.js             # 부트스트랩: 세션 복원 → 라우터 시작
   ├─ router.js          # 해시 라우팅(#/walk, #/diary, #/room/:id ...)
   ├─ api.js             # fetch 래퍼(토큰 헤더, 에러 표준화)
   ├─ store.js           # localStorage 세션(user_id, auth_token, 설정)
   ├─ polling.js         # 주기 조회 유틸(요청 수신/방 갱신)
   └─ screens/           # 화면별 렌더 모듈 (아래 매핑)
```

### 클라이언트 상태 (localStorage)
| 키 | 값 |
|---|---|
| `auth_token` / `user_id` | 게스트 세션 (`POST /auth/guest` 결과) |
| `pet_id` | 내 반려동물 |
| `active_walk_session_id` | 진행 중 산책 |
| `settings` | 위치 공유/대략 위치/기본 공개범위 |

---

## 화면 ↔ 모듈 매핑

| SCR | 모듈 | 사용 API |
|---|---|---|
| SCR-01 로그인 | `screens/auth.js` | `POST /auth/guest` |
| SCR-02·31 프로필 | `screens/pet.js` | `POST/PATCH /pets`, `GET /auth/me` |
| SCR-10 홈 | `screens/home.js` | `GET /auth/me`, 오늘의 퀘스트 미리보기 |
| SCR-11 산책 지도 | `screens/walk_map.js` | `walks/start`, `walks/{id}/location`, `nearby/dogs` |
| SCR-12 미리보기 | `screens/peek.js` | `nearby` 응답 |
| SCR-13 요청 대기 | `screens/request.js` | `match-requests`, polling `incoming` |
| SCR-14 매칭 세션 | `screens/session.js` | `match-sessions/{id}`, `end` |
| SCR-20 기록 에디터 | `screens/record_edit.js` | `clips/upload`, `records` |
| SCR-21 다이어리 | `screens/diary.js` | `GET /records` |
| SCR-22 기록 상세 | `screens/record_view.js` | `records/{id}`, `clips/{id}/stream` |
| SCR-23~26 방 | `screens/room*.js` | `rooms*`, `reactions` |
| SCR-27 오늘의 퀘스트 | `screens/quest.js` | `quests/candidates|select|today` |
| SCR-30·32 마이/설정 | `screens/settings.js` | `privacy/*` |

### 탭바
산책(`#/walk`) · 기록(`#/diary`) · 마이(`#/my`) — 3탭.

---

## 핵심 구현 1 — 2초 클립 녹화 (F-10)

```
getUserMedia({ video, audio })
  → new MediaRecorder(stream, { mimeType: 'video/webm' })
  → start(); setTimeout(() => recorder.stop(), 2000)   // 2초 강제
  → ondataavailable: Blob 수집
  → onstop: Blob → FormData → POST /api/clips/upload (duration_ms≈2000, mission_id)
  → 미리보기 재생 → 기록 에디터(SCR-20)에 클립 추가
```
- HTTPS/localhost 필수. 권한 거부 시 안내.
- 여러 미션 클립을 모아 `POST /records`의 `clip_ids`로 한 기록에 묶음.

## 핵심 구현 2 — 지도 & 위치 (F-01)

```
MapLibre GL JS(CDN) + OSM raster 타일
navigator.geolocation.watchPosition(pos =>
  PATCH /api/walks/{id}/location { lat, lng })       // 산책 중 주기 갱신
폴링: GET /api/nearby/dogs?lat&lng → 마커 갱신(대략 위치)
마커 탭 → SCR-12 미리보기 → [같이 산책하기] → POST /match-requests
```
- 내 위치 마커 + 근처 강아지 아이콘(거리 라벨) + 필터(크기/성격).
- 산책 종료/이탈 시 `walks/{id}/end` → 내 노출 제거.

## 핵심 구현 3 — 매칭 폴링 (F-03/04)

```
요청 발신자: SCR-13에서 GET /match-requests/{id} 또는 incoming 폴링 → accepted면 SCR-14
요청 수신자: 전역 polling.js가 GET /match-requests/incoming(2~5초) → 배너/수락 UI
```

## 핵심 구현 4 — 퀘스트 (F-12)

```
산책 시작 또는 기록 진입 시:
  GET /quests/candidates(scope=user 또는 room) → locked면 오늘의 퀘스트 표시
  미선택 시 후보 3개 → POST /quests/select → lock
  산책 중 SCR-11 배너/SCR-27에서 미션별 2초 촬영 → mission_id로 클립 연결
  기록 저장 시 daily_quest_id 자동 연결
방 모드: scope=room, scope_id=room_id → 첫 멤버 선택이 방 전체 공유
```

## 핵심 구현 5 — 방 & 반응 (F-11)

```
SCR-24 생성 → join_code 표시/공유(Web Share API, 딥링크)
SCR-26 참여: 6자리 코드 → POST /rooms/{id}/join
SCR-25 상세: GET /rooms/{id} → 타임라인(기록+클립) + 이모지 반응(POST /reactions 토글)
```

---

## UX 메모
- 디자인 토큰/스타일은 [04_ui_ux_style.md](../mvp_planning/04_ui_ux_style.md) 따름.
- 모든 화면 모바일 세로 기준. 로딩/빈 상태/권한 거부 상태를 각 화면에 반드시 둔다.
- 네트워크 실패 시 토스트 + 재시도. 기록 작성 중 이탈은 드래프트(localStorage) 저장.
