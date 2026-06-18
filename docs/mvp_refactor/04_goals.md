# 04 · 리팩토링 실행 `/goal` 분할 (복붙용)

> blip 프론트(`server/static/`)를 듀오링고풍으로 재설계하는 작업을 **4개 goal(R0~R3)로 순서대로** 실행한다.
> 기능/플로우/백엔드는 그대로. 비주얼·IA·모션만 바꾼다.
> 스펙은 `docs/mvp_refactor/00~03`. 기존 `docs/mvp_planning/04_ui_ux_style.md`(글래스+M3)는 이 리팩토링이 대체한다.

공통 원칙(모든 goal 공통, 위반 금지):
- **빌드 스텝 없는 Vanilla JS SPA.** 해시 라우팅, FastAPI가 `server/static/` 서빙. 모듈은 ESM.
  React/Tailwind 컴포넌트(Magic UI·Animata 등) **도입 금지**. 모션은 **Motion One(ESM import)** 또는 CSS만.
- 기존 모듈 구조(`api.js·store.js·router.js·polling.js·ui.js·screens/*`)·localStorage 키 유지. 백엔드 API 그대로.
- **외곽 볼드 선(`border: 1px/1.5px solid var(--outline)`) 전면 제거** — 채움+솔리드 그림자로 분리.
- 모든 입체/모션은 `prefers-reduced-motion` 존중(자동 축소/대체).
- **DoD는 정적 200 체크 금지.** 헤드리스 브라우저(Playwright Chromium)로 실제 클릭/입력해 플로우 통과 +
  **콘솔 에러 0 + before/after 스크린샷 + 실행 로그**로 증명. 기존 `scripts/fe_smoke*.py` 셀렉터가 깨지면
  스모크 러너도 함께 수정한다. conda env는 `alpha-blip`.

> 권장 순서: **R0 → R1 → R2 → R3**. R0·R1 끝나면 한 번 스크린샷으로 확인 후 R2·R3(모션) 진행.

---

## /goal — R0: 디자인 시스템 교체 (글래스 제거 · 입체 버튼/카드 · 외곽선 제거)

```
docs/mvp_refactor/01_design_system.md를 따라 server/static/css/app.css를 듀오링고풍(neo-tactile)으로 전면 리스타일한다. 기능/마크업/라우팅은 건드리지 말고 CSS 위주(+필요 시 ui.js의 클래스명 정리)로만 바꾼다. 범위: (a) :root 토큰 — 코랄 아이덴티티 유지하며 각 컬러롤에 *-shadow(입체 하단색) 추가, --outline 폐기, 입체 깊이 토큰(--depth/--depth-cta/--press/--ambient) 신설, 셰이프/스프링 토큰 정리. (b) 핵심 컴포넌트 — .btn/.cta는 솔리드 면 + "0 depth 0 shadow-color" 하단 입체 + :active translateY 눌림, .card는 테두리 제거 + 소프트 입체, .input/.select/textarea는 outline선 대신 inset box-shadow 채움+focus 컬러, .seg .opt/.tags .tag는 칩형 3D 선택상태, .chip/.badge pill 챙키. (c) 글래스 통일 — .glass/.glass-edge/.sheet를 불투명 화이트 챙키 카드로 재정의(backdrop-filter/반투명 제거), 지도 마커 .dog-marker를 화이트 입체 핀으로, .tabbar는 border-top 제거 + active 챙키 펄. (d) 타이포는 Pretendard 헤비 웨이트로 챙키하게(의존성 0). 모든 transform/모션은 prefers-reduced-motion에서 축소.

완료 조건: (1) app.css에서 'solid var(--outline)' 및 '1.5px solid' grep 결과 0 확인. (2) uvicorn 기동 후 Playwright 헤드리스로 주요 화면(auth/onboard-pet/home/diary/rooms/my)을 차례로 띄워 콘솔 에러 0 + 각 화면 스크린샷(가능하면 재설계 전 커밋 스크린샷과 before/after 비교)을 저장하고, 버튼 :active 눌림이 동작하는지 1개 이상 단언. (3) 기존 scripts/fe_smoke.py(가입→펫 등록→#/home)를 재실행해 그대로 통과하는지 확인(셀렉터 깨지면 러너 수정). (4) 실행 로그(통과 메시지·스크린샷 경로)를 보여준다. 또는 50턴 후 중단.
```

---

## /goal — R1: IA 변경 — 4탭 + 방 로그 피드 승격

```
docs/mvp_refactor/02_information_architecture.md를 따라 방(rooms)을 독립 탭으로 승격하고 방 탭 랜딩을 셋로그풍 세로 로그 피드로 개편한다. R0 산출물 위에서 이어서 한다. 범위: (a) index.html 탭바를 3탭→4탭(산책🐾 #/home / 방🏠 #/rooms / 기록📔 #/diary / 마이🙂 #/my, 방은 data-tab="room"). (b) setTab 재배선 — screens/rooms.js(목록·new·join)와 screens/room_view.js의 setTab("diary")를 setTab("room")으로, screens/diary.js는 "diary" 유지. (c) screens/rooms.js 방 탭 랜딩을 단순 방 목록 → 통합 로그 피드로 개편: 상단 방 필터 칩(전체/방별), 본문은 GET /rooms로 내 방들 받고 각 방 GET /rooms/{id} 타임라인을 클라이언트에서 최신순 병합한 세로 카드 피드(방이름·작성자·시간·썸네일/2초클립·텍스트·이모지반응 집계), 카드 탭→#/room/:id, 하단/헤더에 [방 만들기](#/rooms/new)·[코드로 참여](#/rooms/join). 방 0개면 빈 상태(다음 행동 CTA). 성능 과하면 "최근 활동 방 1개 타임라인 + 칩 전환" 단계안 허용. 디자인은 01_design_system 입체 카드 사용.

완료 조건: uvicorn 기동 후 Playwright 헤드리스로 (1) 탭바가 4개 렌더되고 data-tab="room"이 존재하는지 단언, (2) A 컨텍스트로 게스트/펫 준비→방 탭 클릭→로그 피드 진입(방 있으면 타임라인 카드, 없으면 빈 상태)이 렌더되는지 단언+방 탭 active 확인, (3) UI에서 방 생성→6자리 join_code 노출→B 컨텍스트가 코드로 참여→B가 visibility=room 기록(클립 포함) 공유→A 방 탭 로그 피드에 B의 로그가 보이는지 단언→상세(#/room/:id) 진입까지. scripts/fe_smoke_room.py를 새 IA에 맞게 수정해 통과시키고, 콘솔 에러 0 + 각 단계 스크린샷 저장. 실행 로그로 통과를 보여준다. 또는 60턴 후 중단.
```

---

## /goal — R2: 모션 레이어 (Motion One + motion.js + ui.js 훅인)

```
docs/mvp_refactor/03_motion_spec.md를 따라 모션 레이어를 얹는다. R0·R1 산출물 위에서 이어서 한다. 범위: (a) server/static/js/motion.js 신설 — Motion One을 ESM import("https://cdn.jsdelivr.net/npm/motion@11/+esm")한 래퍼: springIn/staggerIn/sheetUp + 쫄깃한 스프링 토큰(SPRING/SOFT), 모든 함수에 reducedMotion() 가드, CDN 실패 시 요소 opacity 1 fallback. (b) ui.js 훅인 — mount()는 .screen에 springIn(+화면 내 카드 리스트 staggerIn), bottomSheet()는 sheetUp 스프링, celebrate()는 마스코트 팝(스케일 버스트)+컨페티 스프링으로 업그레이드(reduced면 미실행), toast/setTab은 유지하되 탭 active 펄 등장 추가. (c) 화면 적용 — 방 로그 피드(rooms.js)·퀘스트 후보(quest.js) 카드 staggerIn, 기록 저장 시 카드가 캘린더로 안착하는 스프링(record.js/diary.js), 매칭 성사 시 celebrate. 순환 import 주의(motion.js는 ui.js의 reducedMotion만 단방향 import). CSS 마이크로인터랙션(버튼 눌림 등)은 그대로 둔다.

완료 조건: uvicorn 기동 후 Playwright 헤드리스로 (1) motion.js ESM import가 성공하고 앱 전반 콘솔 에러 0인지 확인, (2) 화면 전환·바텀시트 업·방 피드 stagger·매칭 축하가 동작하는지(애니메이션 전후 스타일/스크린샷으로) 단언, (3) prefers-reduced-motion:reduce 컨텍스트로 한 번 더 돌려 모션이 축소되고도 기존 플로우(가입→펫→홈, 방 피드)가 정상 통과하는지 확인, (4) CDN 차단(또는 import 실패) 시에도 화면이 깨지지 않는지 확인. 각 단계 스크린샷 저장, 실행 로그로 통과를 보여준다. 또는 60턴 후 중단.
```

---

## /goal — R3: 화면별 마감 + 전체 회귀 + 문서 갱신

```
docs/mvp_refactor/01~03을 기준으로 화면별 디테일을 마감하고 전체 회귀를 돌린다. R0~R2 산출물 위에서 이어서 한다. 범위: (a) 화면 폴리시 — 홈(home.js) 큰 입체 "산책 시작" 히어로+펫 카드, 퀘스트(quest.js) 후보 stagger, 기록 에디터/저장(record.js) 안착 모션+성공 피드백, 다이어리(diary.js) 스탯 카운트업·연속일수 강조, 빈 상태/로딩/권한거부 상태가 새 디자인으로 일관되게. (b) 잔재 정리 — 남은 글래스/외곽선/구 토큰 사용처 제거, 4탭 전반 시각 일관성 점검. (c) 문서 — docs/mvp_planning/04_ui_ux_style.md 상단에 "→ docs/mvp_refactor로 이관(듀오링고풍 통일·4탭)" 주석 추가, mvp_refactor 스펙과 실제 구현 간 차이가 있으면 스펙을 실제에 맞게 업데이트.

완료 조건: uvicorn 기동 후 scripts/fe_smoke.py·fe_smoke_walk.py·fe_smoke_record.py·fe_smoke_room.py·fe_smoke_settings.py를 전부 재실행해 모두 통과(셀렉터 깨지면 러너 수정), 각 스모크 콘솔 에러 0 + 갱신된 스크린샷 저장. reduced-motion 1회 통과도 포함. 5개 화면군(산책/방/기록/마이/온보딩)의 before/after 스크린샷을 한데 모아 보여주고, 변경 파일 요약과 통과 로그를 제시한다. 또는 60턴 후 중단.
```

---

## /goal — R4: 데모/테스트 모드 (홈 test 키 → 1인 풀플로우)

> R0~R3(리팩토링)와 **독립**한 부가 시연 기능. 스펙은 `docs/mvp_refactor/05_demo_mode.md`.
> 친구(매칭 이력) 개념은 데이터모델에 없어 **제외** — 목업 유저를 멤버로 둔 "데모 방"이 매칭↔방공유를 잇는다.

```
docs/mvp_refactor/05_demo_mode.md를 따라 기기 1대(헤드리스 1세션)에서 산책→매칭→기록→방 공유 전 과정을 시연할 수 있는 데모 모드를 추가한다. 기능/플로우/디자인은 기존(R0~R3) 위에서 이어서.

범위: (백엔드) (a) models.User에 is_mock(default False) 추가. 현재 프로젝트는 Alembic 없이 create_all만 쓰므로 기존 walk.db용 dev 스키마 보정(ALTER TABLE users ADD COLUMN is_mock BOOLEAN DEFAULT 0) 또는 DB reset을 처리한다. (b) 현재 사용자별 목업 유저는 별도 친구/관계 테이블 없이 deterministic auth_token("demo-mock:{current_user.id}")/email sentinel로 멱등 조회하고, 목업 펫을 보장한다. (c) server/api/demo.py 신설 + main.py 등록: POST /api/demo/setup(인증) — 큰길타워 좌표(미지정 시 기본)로 ①현재 유저용 목업 유저(is_mock)+펫 보장 ②목업의 active WalkSession을 큰길타워 인근 ~80m(반경 내)에 is_location_visible=True로 생성/갱신 ③나+목업이 active 멤버인 "데모 방" 보장, 응답에 mock_user_id·mock_walk_session_id·room_id·room_join_code·location 반환(멱등). (d) GET /nearby/dogs에서 is_mock 세션은 auth_token이 "demo-mock:{current_user.id}"인 내 데모 목업만 노출해 일반 nearby 오염을 막는다. (e) 자동 수락 — POST /match-requests의 receiver 세션 소유자가 is_mock이면 services/matching에서 즉시 accept(match_session 생성)하여 기존 대기화면 폴링이 세션으로 전환되게(클라이언트 매칭 플로우 변경 최소).

(프론트) (f) store.js에 blip_demo_context 기반 setDemo/get demo/clearDemo 추가. (g) screens/home.js에 보조 버튼 #demo-setup "🧪 데모 산책 (강남 테헤란로)" — api.post("/demo/setup")→store.setDemo({lat,lng,mockSessionId,roomId})→navigate("/walk"). (h) screens/walk.js는 store.demo가 있으면 geolocation 소스를 데모 좌표로 고정(watchPosition 대신, 데스크톱/헤드리스 GPS 없이 동작)하고 PATCH /walks/{id}/location도 데모 좌표로 — 근처폴링·마커·바텀시트·요청·세션전환은 기존 그대로. 기존 store.walkId가 남아 있으면 데모 시작 전에 정리하거나 데모 좌표로 새 세션을 보장한다. (i) record.js는 친구 리스트 추가 없이 기존 방 공유 흐름 재사용하되 데모 컨텍스트면 visibility="room", roomId=store.demo.roomId를 기본값으로 잡는다. 데모 좌표·라벨은 상수 한 곳에서 관리.

완료 조건: uvicorn 기동 후 Playwright 헤드리스 1세션(geolocation 큰길타워 주입 + 카메라/마이크 fake)으로 scripts/fe_smoke_demo.py를 신설해 통과시킨다: (1) 게스트/펫 준비→홈 #demo-setup 클릭→/api/demo/setup 200→#/walk 진입, (2) 지도에 목업 마커(nearby) 노출 단언→마커 탭→바텀시트→[같이 산책하기], (3) 자동 수락으로 매칭 세션(SCR-14) 전환 단언, (4) [산책 종료]→기록 에디터→2초 클립 녹화 201→공개범위 [방 공유]→데모 방 선택→저장, (5) 방 탭 로그 피드(또는 데모 방 상세)에 방금 로그 노출 단언. 콘솔 에러 0(외부/WebGL 잡음 제외) + 각 단계 스크린샷 저장. 기존 fe_smoke.py·fe_smoke_walk.py·fe_smoke_room.py가 여전히 통과하는지(회귀)도 확인. 실행 로그로 통과를 보여준다. 또는 60턴 후 중단.
```

---

## 부록 — 스모크 러너 매핑(참고)

| 러너 | 커버 |
|---|---|
| `scripts/fe_smoke.py` | 가입→펫 등록→#/home (FE0) |
| `scripts/fe_smoke_walk.py` | 산책/지도/매칭 |
| `scripts/fe_smoke_record.py` | 2초 클립·기록·다이어리 |
| `scripts/fe_smoke_room.py` | 방 생성/참여/타임라인/반응 (**R1에서 수정 필요**) |
| `scripts/fe_smoke_settings.py` | 마이/설정 |
| `scripts/fe_smoke_demo.py` | 데모 모드: 산책→매칭(자동수락)→기록→방공유 (**R4에서 신설**) |
