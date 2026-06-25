# 10 · W0 — 기반/공통 (먼저 머지)

> **이 패키지가 제일 먼저 끝나고 통합 브랜치에 머지된다.** 공용 파일(탭바·라우트·공용 헬퍼·키)을 확정하고,
> W1~W6이 만질 **빈 스텁 화면 파일**을 미리 만들어 이후 병렬 작업의 충돌을 0으로 만든다.
> 먼저 읽기: [`00_orchestration.md`](00_orchestration.md), [`01_overview.md`](01_overview.md).

브랜치: `feat/v2-W0-foundation` ← `feat/v2-redesign`

---

## 1. 목표
1. 하단 탭 3개(기록/홈/마이)로 교체.
2. 신규 라우트 7종 **선등록** + 빈 스텁 모듈 생성(W1~W6용).
3. 공용 헬퍼 `centerModal` 추가, `store`에 산책 클립 누적 키 추가.
4. 랭킹/방/업적 **프론트 숨김**(진입점·공유옵션 제거). 백엔드는 손대지 않음.

## 2. 범위 (수정 파일)
- `server/static/index.html` — 탭바.
- `server/static/js/app.js` — 라우트 테이블.
- `server/static/js/ui.js` — `centerModal` 추가(+`setTab` 3탭 확인).
- `server/static/js/store.js` — 클립 누적 키.
- `server/static/js/screens/my.js` — 랭킹/업적/방 링크 제거.
- `server/static/js/icons.js` — 필요한 신규 아이콘 path 추가(`map`, `phone-off`, `footprints`, `smile` 등).
- **신규 빈 스텁**: `screens/{home_map,walking,matching,camera,record_tab,pet_diary}.js`.

## 3. 상세

### 3.1 탭바 (`index.html` 24~30 교체)
현재 5탭(산책🐾/방🏠/기록📔/랭킹🏆/마이) → **3탭(좌→우: 기록/홈/마이)**:
```html
<nav class="tabbar hidden" id="tabbar">
  <a href="#/diary" data-tab="diary"><span class="ic" data-icon="notebook"></span><span>기록</span></a>
  <a href="#/home"  data-tab="home"><span class="ic" data-icon="map"></span><span>홈</span></a>
  <a href="#/my"    data-tab="my"><span class="ic" data-icon="circle-user"></span><span>마이</span></a>
</nav>
```
- `hydrateIcons()`가 `data-icon`을 치환하므로 `map` 아이콘 path를 `icons.js`에 추가.
- `ui.js`의 `setTab(name)`은 `data-tab` 비교라 코드 변경 불필요(새 값 `"home"` 자동 지원). `setTab("walk")` 호출처는 W1에서 `"home"`으로 바뀜.

### 3.2 라우트 선등록 (`app.js` 30~57 영역)
W1~W6이 app.js를 건드리지 않도록 **W0가 모든 라우트를 미리 등록**한다(스텁 import).
```js
import { homeMapScreen } from "./screens/home_map.js";      // W1
import { walkingScreen } from "./screens/walking.js";       // W2
import { matchingScreen } from "./screens/matching.js";     // W3
import { cameraScreen } from "./screens/camera.js";         // W4
import { recordTabScreen } from "./screens/record_tab.js";  // W5
import { petDiaryNewScreen, petDiaryViewScreen } from "./screens/pet_diary.js"; // W6

route("/home", homeMapScreen);          // 홈 = idle 지도 (구 homeScreen 대체)
route("/walk", walkingScreen);          // 산책 중 (구 walkScreen 대체)
route("/matching/:id", matchingScreen); // 신규
route("/camera", cameraScreen);         // 신규
route("/diary", recordTabScreen);       // 기록 탭 (구 diaryScreen 대체)
route("/pet-diary/new", petDiaryNewScreen);   // 신규
route("/pet-diary/:id", petDiaryViewScreen);  // 신규
```
- 구 `homeScreen`/`walkScreen`/`diaryScreen` import는 제거(파일은 남겨도 무방, 라우트만 새 스텁으로).
- `#/quest`, `#/record`, `#/record/:id` 라우트는 **흐름에서 제거**(등록 삭제). 핸들러 파일은 dormant.
- `#/request/:id`, `#/session/:id`는 W3가 `/matching`으로 흡수하므로 **남겨두되**(기존 매칭 백업 경로) W3가 정리.
- 방/랭킹/업적 라우트(`/rooms*`, `/league`, `/achievements`, `/pets`, `/settings`)는 **등록 유지(dormant)** — 진입점만 제거. (라우트까지 지우면 my.js 등에서 깨질 수 있어 보수적으로 유지.)
- 부트(`app.js` 96~99): `setNotFound`/초기 해시 기본값은 `/home` 유지(이미 그러함).

### 3.3 공용 헬퍼 `centerModal` (`ui.js` 신규)
W1의 "가운데 팝업 프로필"이 쓰는 **중앙 모달**. 기존 `bottomSheet` 패턴(scrim + spring)을 재사용하되 중앙 정렬.
```js
// 화면 가운데 카드 팝업. buildContent(close) → DOM 반환.
export function centerModal(buildContent) { /* overlay-root에 scrim+카드, springMotion으로 등장,
  scrim 클릭/닫기 버튼으로 close. reducedMotion 가드. */ }
```
- 스타일 클래스 `.center-modal`/`.center-modal-card`는 app.css에 W0 배너로 추가(디자인 시스템 입체 카드 규격).
- `celebrate`/`bottomSheet`와 동일하게 `overlay-root`에 마운트, `mount()`가 비워주는 생명주기 준수.

### 3.4 `store` 클립 누적 키 (`store.js`)
산책 중 촬영 클립을 누적/복원(새로고침 내성). 산책/매칭 세션 식별과 함께 저장.
```js
// KEYS에 walkClips: "blip_walk_clips" 추가
get walkClips() { try { return JSON.parse(localStorage.getItem(KEYS.walkClips) || "[]"); } catch { return []; } }
addWalkClip(c) { const l = this.walkClips; l.push(c); localStorage.setItem(KEYS.walkClips, JSON.stringify(l)); }
clearWalkClips() { localStorage.removeItem(KEYS.walkClips); }
// (clip: {clip_id, mission_id|null, order})
```
- `logout()`은 모든 KEYS 제거이므로 자동 정리됨.

### 3.5 랭킹/방/업적 프론트 숨김
- **탭바**: 이미 3탭으로 교체(방/랭킹 제거).
- `screens/my.js` 44~51 링크 카드: **"업적", "내 방" linkRow 제거**, `achievementsCard`(60~85) 호출 제거.
  남길 것: 반려동물 관리/등록, 개인정보 보호 설정, 로그아웃. (업적 API 호출 `api.get("/achievements")`도 제거.)
- `screens/diary.js`는 W5가 `record_tab.js`로 대체하므로 W0는 손대지 않음(단, 라우트는 W0가 새 스텁으로 연결).
- 공개범위 "방 공유" 옵션: 구 `record.js`는 폐기되므로 W0 무관. W5/W4 기록 생성은 항상 `visibility:"diary"`.
- **백엔드 무변경**: `main.py` 라우터 목록, `rooms/leagues/achievements` API/모델/`demo.py` 모두 그대로.

### 3.6 빈 스텁 모듈 규약
각 스텁은 export 시그니처만 갖춘 placeholder(임시로 `mount(el("div.stack",{},[el("h1.h1",{text:"<W?> 준비 중"})]))`).
W1~W6이 이 파일을 통째로 구현한다. **시그니처 고정**(아래)을 지켜 app.js가 안 깨지게:
```
home_map.js : export async function homeMapScreen() {}
walking.js  : export async function walkingScreen() {}
matching.js : export async function matchingScreen(params) {}      // params.id
camera.js   : export async function cameraScreen(_p, query) {}     // query.mission, query.quest
record_tab.js: export async function recordTabScreen(_p, query) {} // query.date?
pet_diary.js: export async function petDiaryNewScreen(_p, query) {}  // query.date?
              export async function petDiaryViewScreen(params) {}    // params.id
```

## 4. 의존성 / 주의
- 선행: 없음(가장 먼저). 통합 브랜치에 **머지 완료 후** W1~W6 시작.
- app.css 수정은 `/* === W0: tabs/center-modal === */` 배너로 파일 끝에 append.

## 5. 완료 조건 (DoD)
1. Playwright 헤드리스: 가입→펫 등록 후 **탭바 3개**(`data-tab`이 정확히 `diary/home/my`)인지 단언. 방/랭킹 탭 부재 단언.
2. `#/home`,`#/walk`,`#/matching/x`,`#/camera`,`#/diary`,`#/pet-diary/new`로 직접 이동 시 **스텁이 렌더되고 콘솔 에러 0**.
3. 마이 화면에 업적/내 방 링크 부재 단언, 로그아웃 정상.
4. `centerModal`을 임시 호출해 중앙 팝업 등장/닫힘 1회 단언(또는 W1 인수인계용 데모).
5. 기존 `scripts/fe_smoke.py`(가입→펫→홈)가 새 탭/홈 스텁 기준으로 통과하도록 러너 수정.
6. 스크린샷(탭바·마이) + 실행 로그 제시. 또는 40턴 후 중단.
