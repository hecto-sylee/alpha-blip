# 12 · W2 — 산책 중 (혼자/매칭 공통 HUD)

> 활성 산책 지도 + 상단 투명 퀘스트박스 + 좌하단 촬영 + 우하단 통화종료. 종료 시 누적 클립으로 기록 생성.
> 먼저 읽기: [`00_orchestration.md`](00_orchestration.md), [`01_overview.md §3.3`](01_overview.md).

브랜치: `feat/v2-W2-walking` ← (W0 머지 후) `feat/v2-redesign`
담당 파일: **`server/static/js/screens/walking.js`**. 공용 파일 수정 금지.

---

## 1. 목표 (손그림 요구 → 구현)

| # | 요구 | 구현 |
|---|---|---|
| 1 | 상단 투명 퀘스트 2개(지도 안 가림) | `.walk-quests` 오버레이, 미션 2개 한 줄 박스. `pointer-events` 박스만 |
| 2 | 퀘스트 탭 → 카메라(퀘스트 표기) | `navigate('/camera?mission=<id>&quest=<제목>')` |
| 3 | 촬영 후(미종료) → 산책중 복귀 + 퀘스트 완료 | 카메라가 복귀(W4), 복귀 시 미션 done 갱신 |
| 4 | 좌하단 일반 촬영 → 카메라 | `navigate('/camera')` (mission 없음) |
| 5 | 우하단 통화종료 → 종료 → 기록 | walk/match end → `POST /records`(누적 클립) → `#/diary` |

## 2. 화면 구성
- `setTab(null)` (몰입 모드, 탭바 숨김).
- 지도: 기존 `walk.js`의 maplibre + `OSM_STYLE` + 본인/주변 마커 로직 재사용.
  - 매칭 산책이면 상대 마커도 표시(동행). 혼자면 주변 표시는 선택(요구엔 없음 → 최소화 가능).
- **상단 퀘스트 오버레이**(투명): `.walk-overlays-top` 안에 `.walk-quests`(미션 박스 최대 2개).
  - 각 박스: 한 줄 텍스트(미션 title), 완료되면 체크 표시. **반투명/유리 아님** — 디자인 시스템상
    "투명 레이아웃"은 *지도를 가리지 않는 가벼운 카드*로 해석(불투명 작은 칩/박스, 그림자 약하게).
- **좌하단**: 일반 촬영 버튼(`icon("camera")`, 둥근 입체 버튼).
- **우하단**: 통화종료 버튼(`icon("phone-off")`, danger 입체 버튼).

## 3. 퀘스트 확보 (picker 폐기)
- 진입 시 `GET /quests/today?scope=user`. locked면 그 미션 사용.
- 미선택이면 `GET /quests/candidates?scope=user` → 후보 1개 **자동 select**(`POST /quests/select`) → 미션 노출.
- 미션 최대 2개만 박스로(나머지 무시). `daily_quest_id` 보관(기록 생성 시 첨부).

## 4. 클립 누적 ↔ 카메라 계약 (W4와 합의)
- 카메라(W4)가 클립 업로드 후 `store.addWalkClip({clip_id, mission_id, order})` 하고 산책중으로 복귀.
- 산책중은 복귀 시 `store.walkClips`를 읽어 **퀘스트 완료 상태**(해당 mission_id 클립 존재) 갱신.
- 진입 출처 식별: 카메라는 복귀 라우트를 `#/walk`로(미종료). 종료상태 표식은 store/플래그로 W4가 판단.

## 5. 종료 → 기록 생성
통화종료 버튼:
```
// 매칭이면 match-session end, 혼자면 walk end
if (matchId) await api.post(`/match-sessions/${matchId}/end`, { duration_minutes: mins });
else         await api.post(`/walks/${walkId}/end`, {});
const clip_ids = store.walkClips.map(c => c.clip_id);
const payload = { visibility: "diary", walked_at: todayStr(), clip_ids, daily_quest_id };
if (matchId) payload.match_session_id = matchId; else payload.walk_session_id = walkId;
await api.post("/records", payload);
store.clearWalkClips(); store.setWalkId(null);
navigate("/diary?saved=1");
```
- `visibility`는 항상 `"diary"`(방 공유 제거).
- 매칭/혼자 식별: 산책 세션이 match에서 시작됐는지(W3가 넘긴 `store`/쿼리) 또는 진입 쿼리 `?match=<id>`.

## 6. 매칭 산책 진입 경로
- W3 [매칭 성공] → `#/walk?match=<match_session_id>`로 진입(또는 store에 matchId 보관).
- 혼자 산책: W1 [산책하기] → `#/walk`(walkId만).
- W2는 두 경우를 쿼리/스토어로 구분해 동일 HUD 렌더, 종료 분기만 다름(§5).

## 7. 의존성 / 주의
- 선행: **W0**(라우트/`store.walkClips`/`phone-off`,`camera` 아이콘). **W4**(클립 계약)와 인터페이스 합의.
- 카메라/기록탭/매칭 화면 자체는 W4/W5/W3 소관 — W2는 navigate + 계약만.
- app.css는 `/* === W2: walking === */` 배너로 append.

## 8. 완료 조건 (DoD)
1. `#/walk` 진입(데모/매칭) → 지도 + 상단 퀘스트 박스(≤2, 지도 가림 없음) + 좌하단 촬영 + 우하단 종료 렌더, 콘솔 0.
2. 퀘스트 박스 탭 → `#/camera?mission=...&quest=...` 진입 단언. 좌하단 탭 → `#/camera`(mission 없음) 단언.
3. (모킹/실촬영) 카메라 복귀 후 산책중에서 해당 퀘스트가 **완료 표시**되는지 단언.
4. 우하단 종료 → end API 호출 + `POST /records`(누적 clip_ids 포함) 201 → `#/diary` 진입 단언. 누적 클립 초기화 확인.
5. before/after 스크린샷 + 로그. `scripts/fe_smoke_walk.py`/`fe_smoke_record.py` 산책중 부분 수정. 또는 60턴 후 중단.
