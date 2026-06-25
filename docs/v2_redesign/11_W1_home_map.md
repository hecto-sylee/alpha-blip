# 11 · W1 — 홈 지도(idle) — *이미지 1*

> 앱 진입 기본 화면. 지도 위에 주변 강아지(모두) + 본인(중앙 빨강). 탭으로 산책/매칭 진입.
> 먼저 읽기: [`00_orchestration.md`](00_orchestration.md), [`01_overview.md §3.1`](01_overview.md).

브랜치: `feat/v2-W1-home-map` ← (W0 머지 후) `feat/v2-redesign`
담당 파일: **`server/static/js/screens/home_map.js`** (스텁 구현). 그 외 공용 파일 수정 금지.

---

## 1. 목표 (손그림 요구 → 구현)
기존 `walk.js` 지도 레이어를 **idle 모드**로 재구성한다(산책 세션 미시작).

| # | 요구 | 구현 |
|---|---|---|
| 0 | "오늘의 퀘스트" 배너 삭제 | `walk.js`의 `#quest-banner`/`loadQuestBanner` **미포함** |
| 1 | 축척 확대 + 본인 중앙 빨강 | map `zoom` ↑(예 16~17), 본인 마커 `.me-marker.red`(빨간 도트, 화면 중앙 유지) |
| 2 | 주변 사용자 = 강아지만 | 마커에서 이름/거리 메타 칩 제거 → 강아지 캐릭터 핀만 |
| 3 | 마커 탭 → 가운데 팝업 | `bottomSheet` 대신 **`centerModal`**(W0 제공)로 프로필+CTA |
| 4 | 타 강아지 → [같이 산책하기] → 매칭중 | `POST /match-requests` → `#/matching/:id` |
| 5 | 본인 강아지 → [산책하기] → 산책중 | 산책 세션 start → `#/walk` |

## 2. 화면 구성
- `setTab("home")` (idle 홈은 탭바 표시).
- 전체화면 지도(`#walk-map`, 기존 `OSM_STYLE`/maplibre 재사용). WebGL 불가 시 fallback 리스트(기존 패턴).
- 본인 마커: **빨간 원형 마커**(`.me-marker`에 빨강 변형). 지도를 본인 좌표로 `center` 고정(이동 시 recenter).
  - 본인 마커도 **탭 가능** → 본인용 centerModal(아래 4).
- 주변 강아지: `GET /nearby/dogs`로 폴링(기존 `refreshNearby`), 마커는 **강아지 캐릭터만**(메타 제거한 `dogMarker` 변형).
- 퀘스트/종료/카운트 등 산책중 HUD는 **없음**(여긴 idle).

## 3. 데이터 / 위치
- 위치: 데모면 `store.demo` 좌표, 아니면 `getOnce()`/`watch()`(기존 `geo.js`). idle이라 **walk session 불필요**.
- 주변: `GET /nearby/dogs?latitude&longitude&radius_meters=1000`. (idle에선 내 위치를 broadcast하지 않으므로
  남에게 안 보일 수 있음 — 정상. nearby는 active walk 세션만 반환.)
- 데모 목업 강아지 마커는 기존 `addDemoPeerMarker` 패턴 재사용 가능.

## 4. center modal (프로필 팝업)
`centerModal((close)=>{...})`로 가운데 카드:
- 공통: 강아지 캐릭터(`petCharacterEl`), 이름/견종/거리/성격 태그(기존 `openPreview` 콘텐츠 이식).
- **타 사용자**: CTA [같이 산책하기]
  ```
  // 본인 active walk session 보장(없으면 POST /walks/start) → 요청
  await api.post("/match-requests", { receiver_walk_session_id: dog.walk_session_id })
  → navigate(`/matching/${res.match_request_id}`)
  ```
  - ⚠️ O1: requester walk session 도출 방식 확인(`server/api/matches.py`). idle에서 요청 불가하면
    "같이 산책하기" 클릭 시 **본인 산책 세션을 먼저 start**한 뒤 요청(이미 위 흐름에 반영).
- **본인**: CTA [산책하기]
  ```
  // 세션 보장: store.walkId 없으면 POST /walks/start {pet_id, lat, lng} → store.setWalkId
  store.clearWalkClips()           // 새 산책 시작 → 누적 클립 초기화
  → navigate("/walk")
  ```
- 닫기: scrim/닫기버튼. 디자인: 듀오링고 입체 카드(인라인 스타일 금지).

## 5. 본인 마커 식별
- nearby 결과에는 보통 **본인이 제외**됨(matches/nearby가 self 제외). 따라서 "본인 강아지"는 nearby가 아니라
  **내 GPS 위치의 별도 빨간 마커**로 직접 그린다. 그 마커 탭 → 본인 centerModal.

## 6. 의존성 / 주의
- 선행: **W0**(centerModal, `#/home`→`homeMapScreen`, `#/walk`/`#/matching` 라우트, `store.clearWalkClips`).
- W2(산책중)·W3(매칭중)으로 navigate만 함(그 화면 구현은 W2/W3 소관).
- app.css는 `/* === W1: home-map === */` 배너로 append(본인 빨강 마커, 강아지-only 핀, center-modal 본문 등).

## 7. 완료 조건 (DoD)
1. 앱 진입 → `#/home`에 지도 렌더, **본인 빨간 마커가 중앙**, 콘솔 에러 0(타일/WebGL 잡음 제외).
2. 주변 강아지 마커가 **강아지 캐릭터만**(이름/거리 칩 없음)인지 단언. 데모 컨텍스트로 목업 마커 1개 확인.
3. 타 강아지 탭 → centerModal → [같이 산책하기] → `POST /match-requests` 200 → `#/matching/:id` 진입 단언.
4. 본인 마커 탭 → [산책하기] → 산책 세션 생성 → `#/walk` 진입 단언.
5. before/after 스크린샷 + 로그. `scripts/fe_smoke_walk.py`의 홈/지도 부분을 새 구조로 수정. 또는 50턴 후 중단.
