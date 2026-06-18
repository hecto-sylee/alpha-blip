# 프론트엔드 구현 `/goal` 분할 (복붙용)

> 백엔드 API(03_api_spec)·데이터모델(02)은 이미 구현·검증됨. 여기서는 **04_frontend_spec.md**의
> 실제 화면(SCR-01~32)을 **04_ui_ux_style.md**(지도=Liquid Glass / 기록=Material 3 Expressive,
> 스프링 모션)대로 만든다. 5개 goal을 **순서대로** 실행한다.
>
> ★ 지난 백엔드 goal들은 DoD가 전부 curl이라 UI가 껍데기로 남았다. 그래서 **모든 프론트 goal의
> DoD는 "헤드리스 브라우저(Playwright Chromium)로 실제 화면을 클릭/입력해 플로우를 통과시키고,
> 콘솔 에러 0 + 스크린샷 + 실행 로그로 증명"** 으로 잡는다. 정적 200 체크로 끝내지 않는다.

공통 원칙(모든 goal 공통, 위반 금지):
- 빌드 스텝 없는 Vanilla JS SPA, 해시 라우팅(`#/walk` 등), FastAPI가 `server/static/` 서빙.
- 04_frontend_spec의 모듈 구조(`api.js·store.js·router.js·polling.js·screens/*`)·localStorage 키
  (`auth_token·user_id·pet_id·active_walk_session_id·settings`)를 따른다.
- 04_ui_ux_style 반영: 지도/산책은 글래스 패널·바텀시트, 기록/다이어리는 볼드컬러·squircle 카드,
  화면당 단일 CTA, 스프링 전환, 마이크로인터랙션, `prefers-reduced-motion` 존중, 터치타깃≥44px, 모바일 세로.
- 백엔드 API는 그대로 사용(필요한 버그만 수정). MapLibre·지도 타일은 CDN.
- 각 화면에 로딩/빈 상태/권한 거부 상태를 둔다.

---

## /goal — FE0: 파운데이션 + 디자인 시스템 + 온보딩

```
docs/mvp_spec/04_frontend_spec.md와 docs/mvp_planning/04_ui_ux_style.md를 따라 blip 프론트 SPA의 토대를 만든다. 백엔드 API(server/)는 이미 구현되어 있으니 그대로 사용한다. 범위: (a) 앱 셸 index.html(헤더 + 뷰 컨테이너 #app + 하단 3탭바: 산책/기록/마이), (b) js 인프라 — api.js(토큰 헤더+에러 표준화 fetch 래퍼), store.js(localStorage 세션: auth_token·user_id·pet_id·active_walk_session_id·settings), router.js(해시 라우팅), polling.js(주기조회 유틸), ui.js(DOM 헬퍼·토스트·바텀시트·스프링 전환·prefers-reduced-motion), app.js(부트스트랩→세션복원→라우터), (c) css/app.css 디자인 시스템 — 04_ui_ux_style의 2-레이어(지도=Liquid Glass 글래스 패널/블러, 기록=Material 3 Expressive 볼드컬러/squircle), 단일 CTA, 스프링 모션 토큰, 토스트, 탭바, (d) 화면 SCR-01 로그인(POST /auth/guest), SCR-02 반려동물 등록(POST /pets, 필수항목 검증·미입력시 다음 비활성). 미가입이면 #/auth, 가입했고 펫 없으면 #/onboard-pet, 둘 다 있으면 #/home으로 라우팅.

완료 조건: (1) conda env alpha-blip에 Playwright+Chromium을 설치하고 재사용 가능한 헤드리스 스모크 러너(scripts/fe_smoke.py 등)를 만든다. (2) uvicorn 기동 후 헤드리스 브라우저로 http://localhost:8000 접속→닉네임 입력해 게스트 가입→반려동물 폼(이름·견종·크기·성격태그 등) 입력·제출→#/home 진입까지 실제 클릭/입력으로 통과시키고, 각 단계 DOM 단언 + 콘솔 에러 0 + 단계별 스크린샷 저장. (3) 그 실행 로그(통과 메시지·스크린샷 경로)를 보여준다. 또는 50턴 후 중단.
```

---

## /goal — FE1: 산책 지도 · 근처 · 매칭 (Liquid Glass 레이어)

```
docs/mvp_spec/04_frontend_spec.md(핵심구현 2·3)와 docs/mvp_planning/04_ui_ux_style.md(지도=Liquid Glass, 매칭성사 축하모션)를 따라 산책/매칭 화면을 구현한다. FE0의 셸·인프라·디자인시스템 위에서 이어서 만든다. 범위: SCR-10 홈(큰 [산책 시작] CTA, 내 펫 요약, 위치권한 상태), SCR-11 산책 지도(MapLibre GL JS CDN + OSM 타일, navigator.geolocation.watchPosition→PATCH /walks/{id}/location 주기 갱신, GET /nearby/dogs 폴링으로 글래스 칩 마커 갱신, 오늘의 퀘스트 미션 배너, [산책 종료]), SCR-12 상대 미리보기 글래스 바텀시트(스프링 업, [같이 산책하기]→POST /match-requests), SCR-13 요청 대기/결과(incoming 또는 상태 폴링, 취소), SCR-14 매칭 세션(GET /match-sessions/{id}, 동행시간, [산책 종료]→POST end). 위치권한 거부·근처 0명 빈 상태 포함. active_walk_session_id를 store에 보관.

완료 조건: uvicorn 기동 후 Playwright 헤드리스(geolocation 좌표 주입 + 권한 grant)로, 사용자 A 세션에서 산책 시작→지도/내 위치 마커 렌더 확인. 사용자 B는 API로 산책+위치 세팅(픽스처)한 뒤, A 화면의 nearby 폴링이 B 마커를 띄우는지 단언→마커 탭으로 글래스 바텀시트 노출 단언→[같이 산책하기]로 요청 전송→B는 API로 accept→A 화면이 세션(SCR-14)으로 전환되는지 단언→[산책 종료]까지. 콘솔 에러 0, 각 단계 스크린샷 저장. 실행 로그로 통과를 보여준다. 또는 60턴 후 중단.
```

---

## /goal — FE2: 기록 에디터 · 2초 클립 · 다이어리 · 퀘스트 (M3 Expressive 레이어)

```
docs/mvp_spec/04_frontend_spec.md(핵심구현 1·4)와 docs/mvp_planning/04_ui_ux_style.md(기록=Material 3 Expressive, 저장시 카드가 캘린더로 안착하는 스프링 모션, squircle 카드)를 따라 기록/퀘스트 화면을 구현한다. 앞 FE goal 산출물 위에서 이어서 만든다. 범위: SCR-27 오늘의 퀘스트(GET /quests/candidates 후보3개→POST /quests/select lock, 미션 리스트 "지금 찍어볼 순간"), SCR-20 기록 에디터(getUserMedia+MediaRecorder로 2초 WebM 강제 녹화→POST /clips/upload, 미션별 클립 모음, 텍스트, 공개범위 일기/방 선택, 자동정보(날짜·시간·거리), [저장]→POST /records에 clip_ids 연결, daily_quest 자동연결), SCR-21 다이어리(GET /records 캘린더+썸네일+스탯 누적거리·횟수·연속일수), SCR-22 기록 상세(GET /records/{id}, GET /clips/{id}/stream 재생, 수정/삭제). 권한거부·빈 상태·드래프트(localStorage) 포함.

완료 조건: uvicorn 기동 후 Playwright 헤드리스(--use-fake-device-for-media-stream --use-fake-ui-for-media-stream로 카메라/마이크 가짜 스트림, 권한 grant)로, 게스트/펫 준비→오늘의 퀘스트 후보3개 노출 확인→1개 select(lock)→기록 에디터에서 2초 클립 녹화가 실제로 stop되고 업로드 201되는지 단언→텍스트 입력 후 저장→다이어리 캘린더/목록에 방금 기록과 연결된 클립이 보이는지 단언→기록 상세 진입까지. 콘솔 에러 0, 각 단계 스크린샷 저장. 실행 로그로 통과를 보여준다. 또는 60턴 후 중단.
```

---

## /goal — FE3: 방 · 타임라인 · 이모지 반응

```
docs/mvp_spec/04_frontend_spec.md(핵심구현 5)와 docs/mvp_planning/04_ui_ux_style.md(방 새 기록 슬라이드 인, squircle 방 카드)를 따라 방 화면을 구현한다. 앞 FE goal 산출물 위에서 이어서 만든다. 범위: SCR-23 방 목록(GET /rooms 방 카드, [방 만들기]·[코드로 참여]), SCR-24 방 생성(이름+모드 walk_friend/family→POST /rooms→join_code 표시), SCR-26 방 초대/참여(6자리 코드 입력→GET /rooms/code/{code} 확인→POST /rooms/{id}/join, Web Share/딥링크 app://join/{code} 공유 버튼), SCR-25 방 상세(GET /rooms/{id} 타임라인: 기록+클립, 클립/기록별 이모지 반응 ❤️😂🔥👍😮 POST /reactions 토글, 멤버목록, 오늘의 방 퀘스트, [기록 올리기]→방 공유 기록(visibility=room) 작성). 빈 상태 포함. FE0의 ?join= 딥링크 진입을 참여 플로우에 연결.

완료 조건: uvicorn 기동 후 Playwright 헤드리스 2개 컨텍스트(A·B)로, A가 UI에서 방 생성→6자리 join_code 노출 단언→B 컨텍스트에서 코드로 참여→B가 방에 visibility=room 기록 공유(클립 포함)→A 방 상세 타임라인에 B의 기록이 보이는지 단언→A가 이모지 반응 토글→타임라인 반응 집계가 갱신되는지 단언. 콘솔 에러 0, 각 단계 스크린샷 저장. 실행 로그로 통과를 보여준다. 또는 60턴 후 중단.
```

---

## /goal — FE4: 마이 · 설정/개인정보 · 전역 폴링 · 마감

```
docs/mvp_spec/04_frontend_spec.md와 docs/mvp_planning/04_ui_ux_style.md를 따라 마이/설정 화면과 전역 마감 요소를 구현한다. 앞 FE goal 산출물 위에서 이어서 만든다. 범위: SCR-30 마이페이지(내 펫 요약·산책 스탯·설정 진입·로그아웃), SCR-31 반려동물 관리/수정(GET·PATCH /pets/{id}), SCR-32 개인정보 보호(위치 공유·대략적 위치·집 주변 비공개·기록 기본 공개범위 토글을 store.settings에 저장, 차단 목록 + POST/DELETE /privacy/block, POST /privacy/report). 전역: polling.js로 받은 매칭 요청(GET /match-requests/incoming 2~5초)을 어느 화면에서나 배너로 노출→수락 UI. 마감: 토스트(스프링 인/아웃, 오류 셰이크), 네트워크 실패 재시도, 모든 화면 로딩/빈/권한거부 상태 점검, prefers-reduced-motion 대체 전환 확인.

완료 조건: uvicorn 기동 후 Playwright 헤드리스로, (1) 설정 화면에서 위치공유/대략위치 토글을 끄고 새로고침해도 store.settings에 유지되는지 단언, (2) 차단 목록에 대상 추가→해제가 UI에서 동작하고 API 2xx인지 단언, (3) B가 API로 A에게 매칭 요청을 보낸 상태에서 A가 임의 화면에 있을 때 전역 폴링 배너가 뜨고 수락 UI가 동작하는지 단언, (4) prefers-reduced-motion=reduce 에뮬레이션에서 축하/스프링 모션이 대체 전환으로 동작(콘솔 에러 0)하는지 확인. 각 단계 스크린샷 저장. 실행 로그로 전체 통과를 보여준다. 또는 60턴 후 중단.
```

---

## 실행 순서 / 팁
- 위 순서대로 FE0→FE1→FE2→FE3→FE4. 앞 goal이 통과해야 다음이 의미 있음.
- FE0에서 만든 `scripts/fe_smoke.py`(Playwright 러너)를 이후 goal이 재사용·확장한다.
- 각 goal은 헤드리스 통과 + 스크린샷이 DoD라 "껍데기 통과"가 구조적으로 불가능하다.
- 폰 실기기/카메라·위치 실동작은 ngrok HTTPS에서 수동 확인(05_android_and_demo, docs/RUN.md).
