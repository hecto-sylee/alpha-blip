# 15 · W5 — 기록 탭 (영상기록 + 펫일기) — *이미지 3·4*

> `#/diary` 전면 재설계. 캘린더/공유 토글, 내 기록영상 + 매칭 상대 기록영상, 펫일기 섹션, 날짜 스와이프.
> 신규 백엔드: 매칭 상대 기록 조회 API + 상대 클립 접근권한.
> 먼저 읽기: [`00_orchestration.md`](00_orchestration.md), [`01_overview.md §3.5`](01_overview.md).

브랜치: `feat/v2-W5-record-tab` ← (**W6 머지 후**) `feat/v2-redesign`
담당 파일: **`screens/record_tab.js`**, `server/api/matches.py`(엔드포인트 추가), `server/api/clips.py`(권한), `server/schemas.py`(append).

---

## 1. 목표 (손그림 요구 → 구현)

| # | 요구 | 구현 |
|---|---|---|
| 1·2 | /diary 대수술 + 방 삭제 | `diary.js` 폐기, 방 버튼/공유옵션 없음 |
| 3 | 상단 둥근 "기록" 칩 → 캘린더/공유 토글 | 칩 탭 → 작은 토글(캘린더/공유). 캘린더=날짜 점프, 공유=비활성 |
| 4 | 내 기록영상 / 매칭 상대 기록영상 | 선택 날짜의 내 record 클립 + (매칭이면) 상대 클립 썸네일 |
| 5 | 하단 펫일기 섹션 | 없으면 "일기가 없어요.", 있으면 *이미지4* 카드 → `#/pet-diary/:id` |
| 6 | 스와이프로 날짜 이동(영상·펫일기 동시) | 좌우 스와이프 → 날짜 prev/next, 두 섹션 동시 갱신 |

## 2. 화면 구성 (`record_tab.js`)
- `setTab("diary")`.
- **상단 바**: 좌측 작은 둥근 칩 `[기록]`(`.record-pill`). 탭 → 토글 메뉴(`캘린더` / `공유`):
  - `캘린더` → 달력 팝업(`centerModal` 또는 인라인) → 날짜 선택 → 해당 날짜로 이동.
  - `공유` → **비활성**(disabled/회색 + 토스트 "준비 중").
- **선택 날짜 상태** `state.date`(기본 오늘, `ymd`).
- **영상 기록 영역**:
  - "내 기록 영상": `GET /records?from=&to=`(선택 날짜)에서 내 record들의 클립 썸네일.
  - "매칭 상대 기록 영상": 해당 날짜 record가 `match_session_id` 있으면 신규 API(§4)로 상대 클립.
    혼자 산책이면 이 영역 **숨김**(내 것만).
  - 썸네일: 인증 Blob video(기존 `recordViewScreen`의 `api.blobUrl(stream_url)` 패턴).
- **펫일기 섹션**(W6 표시 컴포넌트 사용):
  - `GET /pet-diary?date=` → 없으면 빈 상태 "일기가 없어요." + [펫일기 작성](`#/pet-diary/new?date=`).
  - 있으면 *이미지4* 카드(기분 이모지 + 활동 아이콘들 + 텍스트). 탭 → `#/pet-diary/:id`.
- **스와이프**: 본문 영역 좌우 스와이프(터치/포인터) → `state.date` ±1일 → 영상+펫일기 동시 재조회·렌더.
  (간단 구현: `touchstart/touchend` deltaX 임계값. reduced-motion 무관.)

## 3. 데이터 흐름
- 날짜별 record: `GET /records?from=<date>&to=<date>`(records.py가 `from/to` 지원). `visibility==="diary"`만.
- 각 record의 클립: record 응답의 `clips[].stream_url` → `api.blobUrl`.
- 펫일기: W6의 `GET /pet-diary?date=<date>`.
- 매칭 여부: record의 `match_session_id` 유무로 판단.

## 4. 신규 백엔드 — 매칭 상대 기록 조회
**엔드포인트(추가, 신규 라우터 X — `matches.py`에 추가):**
```
GET /api/match-sessions/{session_id}/records   (참여자 전용)
→ 200 {
    mine:    [{ record_id, clips:[{id, stream_url, duration_ms, order}] }],
    partner: [{ record_id, clips:[...] }]
  }
```
- 권한: 현재 사용자가 `match_sessions.user_a_id` 또는 `user_b_id`여야 함(아니면 403).
- 구현: 세션에서 두 user 식별 → `Record where match_session_id == session_id` 조회를 user별 분리 → 각 record의 active 클립 직렬화.
- 스키마는 `schemas.py`에 **append**(W6가 models/schemas 먼저 손대므로 그 뒤 rebase).

**클립 접근권한 확장(`clips.py`):**
- 현재 `GET /clips/{id}/stream`은 owner 또는 방 멤버만 허용(O2).
- **매칭 동행자**가 상대의 *해당 match_session에 연결된* 클립을 볼 수 있도록 분기 추가:
  - 클립의 record가 match_session에 속하고, 현재 사용자가 그 세션 참여자면 허용.
- 범위 최소화: 매칭 record의 클립에 한정(일반 diary 클립은 여전히 owner 전용).

## 5. 의존성 / 주의
- 선행: **W0**(라우트 `#/diary`→`recordTabScreen`, `#/pet-diary` 라우트, `centerModal`).
  **W6**(펫일기 `GET /pet-diary` API + 표시 카드 규약, models/schemas 선점) → **W6 머지 후 rebase**.
- 백엔드 충돌 회피: `schemas.py`/`matches.py`/`clips.py`는 끝/적절 위치에 추가, W6의 models/schemas 변경과 정합.
- app.css는 `/* === W5: record-tab === */` 배너로 append.

## 6. 완료 조건 (DoD)
1. `#/diary` → 상단 [기록] 칩 + 영상 섹션 + 펫일기 섹션 렌더, 방 버튼/공유옵션 부재 단언, 콘솔 0.
2. [기록] 칩 탭 → 캘린더/공유 토글. 캘린더로 날짜 선택 시 해당 날짜 기록으로 이동 단언. 공유는 비활성 단언.
3. (데모 매칭 산책 후) 내 기록영상 + **상대 기록영상 썸네일** 둘 다 표시 단언(신규 API 200 + 상대 클립 stream 200).
   혼자 산책 record는 상대 영역 미표시 단언.
4. 펫일기 0개 → "일기가 없어요." + 작성 진입 / 1개 이상 → 카드 표시 + 상세 진입 단언.
5. 좌우 스와이프 → 날짜 변경 시 영상+펫일기 **동시 갱신** 단언.
6. before/after 스크린샷 + 로그. `scripts/fe_smoke_record.py` 기록탭 부분 수정. 또는 70턴 후 중단.
