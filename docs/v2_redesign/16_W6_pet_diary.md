# 16 · W6 — 펫일기 (백엔드 + 작성/표시) — *이미지 4·5*

> 신규 PetDiary 모델+API. 작성 화면(기분/활동/텍스트), 기록 탭에 표시되는 카드(이미지4).
> 먼저 읽기: [`00_orchestration.md`](00_orchestration.md), [`01_overview.md §3.6·§4.1`](01_overview.md).

브랜치: `feat/v2-W6-pet-diary` ← (W0 머지 후) `feat/v2-redesign`
담당 파일: `server/models.py`, `server/schemas.py`, **`server/api/pet_diary.py`(신규)**, `server/main.py`(라우터 등록),
`server/static/js/screens/pet_diary.js`. (models/schemas/main.py 선점 → W5는 이후 rebase.)

---

## 1. 목표
1. PetDiary 백엔드(모델+CRUD API).
2. 펫일기 작성 화면(`#/pet-diary/new`) — 기분 + 활동 태그 + 텍스트.
3. 펫일기 상세/편집(`#/pet-diary/:id`).
4. 기록 탭(W5)이 쓸 **표시 카드 규약**(이미지4 형태) 제공.

## 2. 백엔드 — PetDiary

### 모델 (`server/models.py`)
```
class PetDiary(Base):  # table "pet_diaries"
    id: str PK (uuid)
    user_id: FK users (index)
    pet_id: FK pets (nullable; 기본 사용자 대표 펫)
    diary_date: Date (index)
    mood: String           # 기분 코드 (예: "happy"|"good"|"soso"|"sad"|"angry" 또는 1~5)
    activity_tags: Text    # JSON list (예: ["weather:sunny","people:friend","meal:lunch"])
    text: Text (nullable)
    created_at: DateTime
```
> create_all 기반이므로 신규 테이블은 자동 생성됨(기존 walk.db에 ALTER 불필요).

### 스키마 (`server/schemas.py`)
- `PetDiaryCreateReq { pet_id?, diary_date, mood, activity_tags:[str], text? }`
- `PetDiaryOut { id, pet_id, diary_date, mood, activity_tags:[str], text, created_at }`
- `PetDiaryListRes { diaries: [PetDiaryOut] }`

### API (`server/api/pet_diary.py` 신규 + `main.py` 등록)
```
POST   /api/pet-diary               (201) → {pet_diary_id}
GET    /api/pet-diary?from=&to=  또는 ?date=  → {diaries:[...]}   # 본인 것만, diary_date 정렬
GET    /api/pet-diary/{id}          → PetDiaryOut (owner only)
PATCH  /api/pet-diary/{id}          → mood/activity_tags/text 수정 (owner)
DELETE /api/pet-diary/{id}          → 삭제 (owner)
```
- `main.py` 라우터 목록에 `pet_diary` 추가(import + include_router). **이 변경은 W6 소유** — W5는 신규 라우터 안 만듦.

## 3. 활동 태그 카탈로그 (이미지 5)
이미지5의 카테고리/아이콘을 코드 카탈로그로 고정(프론트 상수 + 백엔드는 자유 문자열 저장):
- **기분(mood)**: 5단계 얼굴(예: `happy/good/soso/sad/angry`). 이미지5 상단 "어떤 하루였나요?".
- **날씨**: 맑음/흐림/비/눈/바람 → `weather:sunny|cloudy|rain|snow|wind`.
- **사람**: 친구/가족/혼자/지인/낯선사람 → `people:friend|family|alone|acquaintance|stranger`.
- **식사**: 아침/점심/저녁/간식 → `meal:breakfast|lunch|dinner|snack`.
- **이동**: 산책/공원/쇼핑/병원 → `move:walk|park|shopping|hospital`.
- 아이콘은 Lucide(`icon(...)`)로 매핑(없으면 `icons.js`에 추가). 색/표현은 디자인 시스템 칩.

## 4. 프론트 — 작성 (`#/pet-diary/new`)
- `setTab("diary")`. 쿼리 `?date=`로 대상 날짜(기본 오늘).
- 구성(이미지5):
  - "어떤 하루였나요?" + 기분 5단계 선택(`.mood-row`, 한 개 선택).
  - 카테고리별 활동 칩 그리드(날씨/사람/식사/이동) — 다중 선택, 선택 시 입체 on.
  - 텍스트 입력(`textarea.input`, 선택).
  - 저장 CTA → `POST /pet-diary` → `#/diary`(작성 날짜로) 이동.
- 디자인 시스템 칩/세그/입체 버튼 사용, 인라인 스타일 금지.

## 5. 프론트 — 상세/편집 (`#/pet-diary/:id`) + 표시 카드 규약
- 상세: `GET /pet-diary/:id` → 기분/활동/텍스트 표시, 편집(PATCH)·삭제(DELETE).
- **표시 카드(이미지4) 규약** — W5가 import해 재사용할 수 있게 `pet_diary.js`에서 export:
  ```
  export function petDiaryCard(d, { onClick }) // → 기분 이모지 + 활동 아이콘 줄 + 텍스트 한두 줄, 입체 카드
  ```
  W5는 이 함수를 호출해 기록 탭 펫일기 섹션을 그린다(렌더 일관성).

## 6. 의존성 / 주의
- 선행: **W0**(라우트 `#/pet-diary/*`). W5보다 **먼저 머지**(W5가 API+카드 규약에 의존).
- models/schemas/main.py를 W6가 선점 → W5는 W6 머지 후 rebase하여 schema append.
- O3: 펫일기↔산책 record 연결은 현재 **standalone**(date+pet). 필요 시 `record_id` FK 후속 검토.
- app.css는 `/* === W6: pet-diary === */` 배너로 append.

## 7. 완료 조건 (DoD)
1. `uvicorn` 기동 → `pet_diaries` 테이블 자동 생성, `POST/GET/PATCH/DELETE /pet-diary` 정상(인증·owner 가드) — API 스모크.
2. Playwright: `#/pet-diary/new?date=오늘` → 기분 선택 + 활동 칩 다중 선택 + 텍스트 → 저장 201 → `#/diary` 이동 단언, 콘솔 0.
3. 저장 후 `GET /pet-diary?date=`에 1건, `#/pet-diary/:id` 상세 표시·편집·삭제 단언.
4. `petDiaryCard`가 이미지4 형태(기분 이모지+활동 아이콘+텍스트)로 렌더되는지 단언(W5 인수인계용).
5. before/after 스크린샷 + 로그. `scripts/fe_smoke_petdiary.py` 신설. 또는 70턴 후 중단.
