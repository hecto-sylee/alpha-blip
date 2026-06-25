# 00 · 중앙 관리 허브 (먼저 읽기) — v2 재설계

> **이 파일은 v2 재설계에 참여하는 모든 worktree 에이전트가 작업 시작 전 가장 먼저 읽는다.**
> (루트 `CLAUDE.md`처럼 동작하지만 자동 로드는 안 되므로, 각 워커는 자기 스펙 문서 + 이 허브 + `01_overview.md`를 명시적으로 읽고 시작한다.)
>
> 역할: ① 불변 규칙(절대 위반 금지) ② 공용 파일 소유권/충돌 방지 ③ 브랜치·머지 순서 ④ 공통 DoD/검증 ⑤ 라우트·상태머신 단일 출처.

---

## 0. 무엇을 만드는가 (한 줄)

blip의 핵심 루프를 **"지도=홈 → (혼자/매칭) 산책 → 카메라 촬영 → 기록(영상+펫일기)"** 으로 재설계한다.
기능 명세 전체는 [`01_overview.md`](01_overview.md), 화면별 구현은 `10~16_W*.md`.

## 1. 불변 규칙 (모든 워커 공통 · 위반 금지)

1. **빌드 스텝 없는 Vanilla JS SPA.** 해시 라우팅, FastAPI가 `server/static/` 서빙. 모듈은 **ESM**.
   React/Tailwind/번들러 도입 **금지**. 모션은 **Motion One(ESM)** 또는 CSS만(`docs/mvp_refactor/03_motion_spec.md`).
2. **디자인은 기존 듀오링고풍(neo-tactile)을 100% 따른다.** 새 디자인 토큰/시스템을 만들지 않는다.
   단일 출처: [`docs/mvp_refactor/01_design_system.md`](../mvp_refactor/01_design_system.md).
   - 외곽 볼드 선 금지(`border: 1px/1.5px solid var(--outline)`), 채움+솔리드 그림자로 분리.
   - 화면 마크업에 인라인 스타일 금지(동적 width 등 제외). `.stack/.row/.card/.cta/.chip` 등 기존 유틸리티 사용.
   - 이모지 대신 `icon("...")`(Lucide) 사용. 새 아이콘은 `server/static/js/icons.js`의 `PATHS`에 추가.
3. **기존 모듈 구조·localStorage 키 유지**: `api.js·store.js·router.js·polling.js·ui.js·screens/*`.
4. **랭킹/방/업적은 "프론트만 숨김"** — 백엔드 라우터/모델/서비스는 **건드리지 않는다**(데이터·복구 보존).
   FE에서 탭·진입점·공유옵션만 제거(상세: `10_W0_foundation.md`).
5. **백엔드 변경은 두 곳에서만 발생**: 펫일기(W6) · 매칭 상대 기록 조회(W5). 그 외 API는 그대로 사용.
6. **DoD는 정적 200 체크 금지.** Playwright 헤드리스로 실제 클릭/입력해 플로우 통과 + 콘솔 에러 0 +
   before/after 스크린샷 + 실행 로그로 증명한다(§5).
7. Python 작업은 conda env **`alpha-blip`** 사용(base 금지).

## 2. 라우트·탭 단일 출처 (이 표가 정답)

### 하단 탭 (3개, 좌→우 순서 고정)

| 위치 | 라벨 | `data-tab` | 라우트 | 아이콘 |
|---|---|---|---|---|
| 좌 | 기록 | `diary` | `#/diary` | `notebook` |
| 중 | 홈 | `home` | `#/home` | `map` |
| 우 | 마이 | `my` | `#/my` | `circle-user` |

> 산책중/매칭중/카메라는 **몰입 모드** → `setTab(null)`로 탭바 숨김.

### 라우트 맵

| 라우트 | 화면 | 탭 | 담당 | 비고 |
|---|---|---|---|---|
| `#/auth`, `#/onboard-pet`, `#/pet/:id` | 인증/온보딩 | null/my | (유지) | 변경 없음 |
| `#/home` | **홈 지도(idle)** | home | **W1** | 앱 진입 기본. 모두 표시, 본인 중앙 빨강 |
| `#/walk` | **산책 중** | null | **W2** | 활성 산책 세션. 퀘스트박스+촬영+종료 |
| `#/matching/:id` | **산책 매칭중**(신규) | null | **W3** | 본인+상대만, 발자국 트래킹, 매칭성공 |
| `#/camera` | **카메라 촬영**(가로) | null | **W4** | `?mission=` / `?quest=` 진입 시 퀘스트 텍스트 |
| `#/diary` | **기록 탭**(재설계) | diary | **W5** | 영상기록+상대기록+펫일기, 캘린더/스와이프 |
| `#/pet-diary/new`, `#/pet-diary/:id` | **펫일기 작성/상세**(신규) | diary | **W6** | 기분·활동·텍스트 |
| `#/my` | 마이(정리) | my | **W0** | 랭킹/업적/방 링크 제거 |
| `#/request/:id`, `#/session/:id` | (구 매칭 대기/세션) | null | W3 흡수 | W3가 `/matching`으로 대체·정리 |
| `#/quest`, `#/record`, `#/record/:id` | (구 퀘스트 picker/기록 에디터) | — | 폐기 | 흐름에서 제거(아래 §3) |
| `#/rooms*`, `#/league`, `#/achievements` | 방/랭킹/업적 | — | 숨김 | 진입점 제거(W0), 핸들러는 dormant |

## 3. 핵심 아키텍처 결정 (전 워커가 동일 전제로 구현)

1. **클립→기록 번들링(at walk-end).** 산책 중 카메라로 찍은 클립들은 **활성 산책 상태에 누적**되고,
   **산책 종료 시 1개의 Record로 묶여 생성**된다(`POST /records` with `clip_ids` + `walk_session_id` 또는 `match_session_id`).
   → 구 `#/record` 에디터(텍스트/공개범위/저장 UI)는 **폐기**. 종료 즉시 기록 생성 후 `#/diary`로 이동.
   누적 클립은 `store`(localStorage 키 `blip_walk_clips`)에 보존해 새로고침 내성 확보.
2. **텍스트/감정 입력 surface = 펫일기**. Record 자체는 영상 클립 + 세션 링크만 가진다(메모 없음).
   사람의 글/기분은 `#/pet-diary`로 분리.
3. **퀘스트는 산책중에서만**. 별도 picker(`#/quest`) 없음. 산책 시작 시 오늘 퀘스트를 **자동 확보**
   (없으면 후보 1개 자동 select)하고 미션 최대 2개를 상단 투명 박스로 노출.
4. **홈(idle)에서 같이 산책하기**: 요청 보내려면 본인 active walk session이 필요할 수 있음
   → "같이 산책하기" 시 **본인 산책 세션을 먼저 보장**(없으면 start)한 뒤 `POST /match-requests` → `#/matching/:id`.
   (구현 시 `matches.py`의 requester_walk_session 도출 방식 확인.)
5. **삭제는 FE 숨김만**(규칙 1.4). 백엔드 무변경.

## 4. 공용 파일 소유권 & 충돌 방지 (병렬 작업 핵심)

> 병렬 worktree 충돌은 **공용 파일**에서만 난다. 아래 소유권을 지킨다.

| 공용 파일 | 소유자 | 다른 워커의 허용 행위 |
|---|---|---|
| `server/static/index.html` (탭바) | **W0** | 수정 금지 |
| `server/static/js/app.js` (라우트 테이블) | **W0** | 수정 금지 — W0가 **모든 신규 라우트를 미리 등록**한다 |
| `server/static/js/ui.js` (공용 헬퍼: `setTab`, `centerModal` 등) | **W0** | 수정 금지(헬퍼 추가 요청은 W0에 반영) |
| `server/static/js/store.js` (키 추가) | **W0** | W0가 `blip_walk_clips` 등 키 추가. 다른 워커는 읽기만 |
| `server/static/css/app.css` | 공유 | 각자 **파일 끝에** `/* === W{n}: <이름> === */` 배너 아래로만 append |
| `server/main.py` (라우터 등록) | **W6** | W5는 신규 라우터 없이 `matches.py`에 엔드포인트 추가(충돌 회피) |
| `server/models.py` / `server/schemas.py` | **W6** 우선 | W5도 schema 추가 필요 → W6 머지 후 rebase하여 append |

**충돌 최소화 전략 (W0의 의무):**
- W0가 **신규 라우트 7종을 app.js에 선등록**하고, `screens/`에 **빈 스텁 모듈**(`home_map.js`, `walking.js`,
  `matching.js`, `camera.js`, `record_tab.js`, `pet_diary.js`)을 미리 만든다.
- 이후 W1~W6은 **자기 스텁 파일 1개만** 채우면 되므로 app.js/index.html을 만질 일이 없다.
- 화면 전용 CSS는 각 워커가 app.css **끝에 배너 섹션으로 append** → 줄 충돌 회피.

## 5. 브랜치 · 머지 순서

- 통합 브랜치: **`feat/v2-redesign`** (현재 `feature/demo-dummies`에서 분기).
- 각 워크패키지: `feat/v2-W0-foundation` … `feat/v2-W6-pet-diary` (통합 브랜치에서 worktree 분기).
- **순서:**
  1. **W0 먼저** 구현·머지(공용 파일/스텁/라우트 확정). → 통합 브랜치 갱신.
  2. W1·W2·W3·W4는 W0 위에서 **병렬**(서로 다른 screen 파일만 수정 → 충돌 없음).
  3. **W6(펫일기 BE+FE) 머지 → W5가 rebase 후** 기록 탭 구현(W5는 펫일기 표시 + 상대기록 API에 의존).
- 머지 전 각 워커는 통합 브랜치 최신을 rebase하고 자기 스모크 재통과 확인.

## 6. 공통 DoD (모든 W 스펙이 상속)

각 W 스펙의 "완료 조건"은 아래를 기본으로 포함한다:
1. `uvicorn` 기동 후 Playwright 헤드리스로 해당 플로우를 **실제 클릭/입력**해 통과.
2. **콘솔 에러 0**(외부 타일/WebGL 잡음 제외) + 화면 **before/after 스크린샷** 저장.
3. 기존 스모크가 깨지면 해당 러너도 함께 수정(부록 §8 매핑).
4. 디자인 회귀 점검: `app.css`에 `solid var(--outline)`/`1.5px solid` 신규 유입 0, 인라인 스타일 0.
5. 실행 로그(통과 메시지 + 스크린샷 경로)를 제시. 또는 N턴 후 중단.

## 7. 글로벌 데이터/엔드포인트 빠른 참조 (확인됨)

- `GET /nearby/dogs?latitude&longitude&radius_meters[&size]` → `{dogs:[{walk_session_id, pet, distance_meters, approximate_location}]}`
- `POST /walks/start {pet_id,latitude,longitude}` → `{walk_session_id,...}` · `PATCH /walks/{id}/location` · `POST /walks/{id}/end`
- `POST /match-requests {receiver_walk_session_id}` → `{match_request_id, expires_at}` · `GET /match-requests/{id}`(폴링) · accept/reject/DELETE
- `GET /match-sessions/{id}` → `{partner:{nickname,pet}, started_at}` · `POST /match-sessions/{id}/end {duration_minutes}`
- `POST /clips/upload`(multipart: file, duration_ms, order, mission_id?) → `{clip_id}` · `GET /clips/{id}/stream`(인증 Blob)
- `GET /quests/today?scope=user` · `GET /quests/candidates?scope=user` · `POST /quests/select`
- `POST /records {visibility,walked_at,clip_ids,daily_quest_id,walk_session_id?,match_session_id?}` · `GET /records` · `GET /records/{id}`
- **신규(W5)**: `GET /match-sessions/{id}/records` → 양측 클립. **신규(W6)**: `/pet-diary` CRUD.

## 8. 스모크 러너 매핑 (영향)

| 러너 | 커버 | v2 영향 |
|---|---|---|
| `scripts/fe_smoke.py` | 가입→펫→홈 | **수정**(홈=지도, 탭 3개) |
| `scripts/fe_smoke_walk.py` | 산책/지도/매칭 | **수정**(홈 idle / 산책중 / 매칭중 분리) |
| `scripts/fe_smoke_record.py` | 클립·기록·다이어리 | **수정**(에디터 폐기, 종료시 자동기록, 기록탭 재설계) |
| `scripts/fe_smoke_room.py`·`fe_smoke_settings.py`·`*league*`·`*achievements*` | 방/랭킹/업적 | 진입점 제거로 **비활성/스킵**(W0) |
| `scripts/fe_smoke_petdiary.py` | 펫일기 | **신설**(W6) |

## 9. 결정/오픈 이슈 추적

확정 결정 4건(2026-06-25): 삭제=프론트만 숨김 · 펫일기=신규 모델 · 상대기록=신규 API · 발자국=프론트 시뮬.
세부 가정/오픈 이슈는 [`01_overview.md` §6](01_overview.md) 참조. 스펙↔구현 차이가 생기면 **스펙을 실제에 맞게 갱신**.
