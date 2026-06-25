# 13 · W3 — 산책 매칭중 (신규)

> 매칭 진행중인 본인+상대만 지도에 표시, 가까워지는 과정에 발자국 트래킹, [매칭 성공] → 산책중.
> 먼저 읽기: [`00_orchestration.md`](00_orchestration.md), [`01_overview.md §3.2`](01_overview.md).

브랜치: `feat/v2-W3-matching` ← (W0 머지 후) `feat/v2-redesign`
담당 파일: **`server/static/js/screens/matching.js`**. 공용 파일 수정 금지.
(구 `screens/match.js`의 요청/세션 로직을 참고·이식하되, 라우트는 `#/matching/:id`로 통합.)

---

## 1. 목표 (손그림 요구 → 구현)

| # | 요구 | 구현 |
|---|---|---|
| 1 | 본인 + 매칭 진행중 상대만 표시 | nearby 전체 숨김, 두 마커만 |
| 1 | 발자국 실시간 트래킹 | 위치 폴링 좌표마다 `footprints` 마커 누적(프론트 시뮬) |
| 2 | 하단 [매칭 성공] 버튼 | 매칭 확정 → `#/walk?match=<id>` |

## 2. 진입 / 상태
- 라우트 `#/matching/:id` (`:id` = `match_request_id`). `setTab(null)`.
- 진입 직후는 **요청 대기**: `GET /match-requests/:id` 폴링(기존 `match.js` `requestWaitScreen` 로직 이식).
  - `accepted` & `match_session_id` → 매칭 세션 확보(상대 위치/프로필 표시 가능).
  - `rejected/expired/cancelled` → 토스트 + `#/home` 복귀.
- 데모 목업은 자동 수락(`matches.py`에서 mock receiver 즉시 accept) → 바로 세션 단계로.

## 3. 지도 / 마커
- 기존 maplibre 지도(OSM). **주변 nearby 폴링 안 함**(매칭중엔 둘만).
- 본인 마커: 빨강(W1과 동일 스타일 재사용 — CSS는 각자 배너로). 상대 마커: 강아지 캐릭터 핀.
- 상대 위치 출처: `GET /match-sessions/:sid`(partner pet) + 위치는 `nearby`/세션 정보로 근사.
  헤드리스엔 GPS 없음(O4) → **데모/시뮬 좌표 보간**으로 상대가 본인 쪽으로 다가오는 애니메이션.

## 4. 발자국 트래킹 (프론트 시뮬)
- 폴링 틱마다(예 2~3s): 본인/상대 현재 좌표를 받아 **직전 위치에 발자국 마커**(`icon("footprints")` 또는 `paw-print`)를 지도에 떨군다.
- 발자국은 누적되며 옅어지는 trail(최근 N개만 유지, 오래된 것 fade/remove).
- 본인 좌표는 `geo.watch`(실기기) 또는 데모 좌표, 상대는 §3 근사. **백엔드 변경 없음**(D4).
- 두 마커 거리 좁혀지면 시각 피드백(가까워짐 강조) — 선택.

## 5. [매칭 성공]
- 하단 입체 CTA. 클릭 시:
  ```
  // 세션 보장: match_session_id 확보(폴링 결과). 산책중으로 인계
  store.clearWalkClips();
  navigate(`/walk?match=${matchSessionId}`);   // W2가 매칭 산책으로 렌더
  ```
- (선택) 성사 모션 `celebrate(myPet)` 재사용.
- 산책 세션/시간 시작 기준은 W2 종료 로직(`/match-sessions/{id}/end`)과 정합되게 둠.

## 6. 의존성 / 주의
- 선행: **W0**(라우트, `footprints` 아이콘, `store.clearWalkClips`). **W2**(`#/walk?match=` 계약).
- 백엔드: 기존 match-requests/match-sessions 그대로 사용(신규 없음).
- 구 `#/request/:id`·`#/session/:id`는 W3가 `/matching`으로 흡수 → 해당 진입(있으면) 정리/리다이렉트.
- app.css는 `/* === W3: matching === */` 배너로 append.

## 7. 완료 조건 (DoD)
1. (데모) W1에서 타 강아지 [같이 산책하기] → `#/matching/:id` 진입, 본인+상대 **둘만** 표시(주변 마커 없음) 단언, 콘솔 0.
2. 폴링으로 발자국 마커가 누적(틱마다 증가)되는지 단언(개수 변화 또는 DOM 카운트).
3. 자동수락(데모)으로 세션 확정 → [매칭 성공] → `#/walk?match=...` 진입 단언.
4. 거절/만료 경로 시 토스트 + `#/home` 복귀 단언.
5. before/after 스크린샷 + 로그. `scripts/fe_smoke_walk.py` 매칭 부분 수정. 또는 60턴 후 중단.
