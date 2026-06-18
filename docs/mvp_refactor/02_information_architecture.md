# 02 · 정보구조(IA) — 4탭 + 방 로그 피드

> 방(rooms)을 `기록(diary)` 탭 아래 중첩에서 **독립 탭으로 승격**하고, 방 탭 랜딩을
> 단순 방 목록 → **셋로그풍 세로 로그 피드**(쌓이는 로그 한눈에)로 개편한다.
> 첫 화면(기본 탭)은 **산책 홈** 유지.

---

## 1. 변경 전 / 후

### 변경 전 (현재)
```
하단 탭 3개:
  산책(walk)  → #/home, #/walk, #/quest
  기록(diary) → #/diary  +  #/rooms, #/rooms/new, #/rooms/join, #/room/:id   ← 방이 여기 묻힘
  마이(my)    → #/my, #/settings, #/pet/:id
```

### 변경 후 (목표)
```
하단 탭 4개:
  산책(walk)  → #/home, #/walk, #/quest
  방(room)    → #/rooms(=로그 피드), #/rooms/new, #/rooms/join, #/room/:id   ← 승격
  기록(diary) → #/diary  (개인 다이어리 캘린더 전용)
  마이(my)    → #/my, #/settings, #/pet/:id
```

라우트(`app.js`의 `route(...)`)는 **그대로**, 탭 매핑(`setTab`)과 탭바 마크업만 바뀐다.

## 2. 탭바 마크업 (`index.html`)

3탭 → 4탭. 방 탭을 산책과 기록 사이에 추가.

```html
<nav class="tabbar hidden" id="tabbar">
  <a href="#/home"  data-tab="walk"><span class="ic">🐾</span>산책</a>
  <a href="#/rooms" data-tab="room"><span class="ic">🏠</span>방</a>
  <a href="#/diary" data-tab="diary"><span class="ic">📔</span>기록</a>
  <a href="#/my"    data-tab="my"><span class="ic">🙂</span>마이</a>
</nav>
```

`ui.js`의 `setTab(name)`은 `data-tab`만 비교하므로 코드 변경 불필요(새 값 `"room"` 자동 지원).

## 3. `setTab` 재배선 (screens)

`grep -rn 'setTab("diary")' server/static/js/screens/` 기준:

| 파일 | 현재 | 변경 |
|---|---|---|
| `screens/rooms.js` (목록 11, new 50, join 93) | `setTab("diary")` | `setTab("room")` |
| `screens/room_view.js` (11) | `setTab("diary")` | `setTab("room")` |
| `screens/diary.js` (12, 110) | `setTab("diary")` | **유지** |

> 그 외 `setTab` 호출(walk/my/null 등)은 변경 없음.

## 4. 방 탭 랜딩 = 로그 피드 (`screens/rooms.js` 개편)

핵심 요구: **"방에 쌓이는 로그가 한눈에"**. snapchal `오늘` 화면처럼 세로 타임라인.

### 레이아웃
```
┌ 방  (헤더)
│ [ 내 방들 칩: 전체 · 방A · 방B ]      ← 방 필터(가로 스크롤 칩)
│ ─────────────────────────────────
│ ▢ 로그 카드  (방이름 · 작성자 · 시간)
│   썸네일/2초클립 · 한 줄 텍스트 · 이모지반응 집계
│ ▢ 로그 카드 ...                       ← 최신순, 스태거 등장(모션 스펙)
│ ─────────────────────────────────
│ [ + 방 만들기 ]  [ 코드로 참여 ]       ← 하단 진입(또는 헤더 우측 +)
└
```

### 데이터 (백엔드 그대로)
- `GET /rooms` → 내가 속한 방 목록(필터 칩 + 빈 상태 판단).
- 각 방 타임라인은 `GET /rooms/{id}`(기존 room_view가 쓰는 것)로 가져와
  **클라이언트에서 최신순 병합**해 통합 피드 구성. (서버 신규 엔드포인트 없이 MVP.)
  - 성능상 과하면: 우선 "가장 최근 활동 방"의 타임라인만 보여주고 칩으로 전환하는 단계적 안도 허용.
- 카드 탭 → 해당 `#/room/:id`(상세) 진입. 방 만들기/참여는 기존 `#/rooms/new`·`#/rooms/join` 재사용.

### 상태
- **빈 상태**(방 0개): 큰 일러스트/이모지 + "첫 방을 만들어 펫 로그를 쌓아보세요" + [방 만들기]/[코드로 참여].
- 로딩: 스피너. 권한/에러: 토스트.

## 5. 기록 탭(`#/diary`)
- 방 분리 후 **개인 다이어리 캘린더 전용**. 기존 `screens/diary.js` 그대로(스타일/모션만 R0·R2에서 갱신).

## 6. 방 상세 참여코드
- 방 상세의 6자리 참여코드는 본문 대형 카드로 상시 노출하지 않는다.
- 좌상단의 작은 `참여코드` 버튼을 누르면 바텀시트 팝업으로 코드와 복사 CTA를 보여준다.
- 스모크는 `#room-code-open` 클릭 후 팝업 안의 `#room-code`를 검증한다.

## 7. 회귀 주의 (스모크)
- `scripts/fe_smoke_room.py`는 방 진입 경로/셀렉터가 바뀌므로 **함께 수정**.
  (예: 방 탭 클릭 → 로그 피드 → [방 만들기]/[코드로 참여] 플로우, 6자리 코드, A/B 컨텍스트 반응 집계.)
- 탭이 3→4개로 늘어 탭바 셀렉터 개수를 단언하는 테스트가 있으면 갱신.

## 8. DoD 체크 (R1)
- [ ] 탭바 4개 렌더, `data-tab="room"` 존재.
- [ ] 방 탭 진입 시 로그 피드(타임라인 카드) 렌더 — 방 있을 때 카드, 없을 때 빈 상태.
- [ ] `rooms.js`/`room_view.js`의 `setTab` → `"room"`, 진입 시 방 탭 active.
- [ ] `fe_smoke_room.py` 새 구조로 통과(콘솔 0 + 스크린샷).
