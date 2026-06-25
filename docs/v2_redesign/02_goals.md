# 02 · 실행 가이드 — worktree별 `/goal` (복붙용)

> v2 재설계를 **worktree 1개 = 워크패키지 1개 = `/goal` 1회**로 실행한다.
> `/goal`은 Claude Code 내장 명령(자동 진행, 완료조건 충족까지 여러 턴). 문법은 [`../mvp_spec/07_goal_command_setup.md`](../mvp_spec/07_goal_command_setup.md).
> 각 프롬프트는 해당 스펙 문서의 DoD를 **실행해 증명 가능한 완료조건**으로 옮긴 것.

---

## 1. 컨벤션 한눈에

| 항목 | 규칙 |
|---|---|
| 통합 브랜치 | `feat/v2-redesign` (현재 `feature/demo-dummies`에서 분기) |
| 워크트리 위치 | `.claude/worktrees/v2-W{n}/` |
| 워크패키지 브랜치 | `feat/v2-W{n}-<이름>` |
| **포트(병렬 충돌 방지)** | W0=9010, W1=9011, W2=9012, W3=9013, W4=9014, W5=9015, W6=9016 |
| 검증 | `PORT=90XX scripts/start.sh` + `BASE=http://localhost:90XX python scripts/fe_smoke_*.py` |
| conda env | `alpha-blip` |

> 워크트리는 각자 `walk.db`를 가져 DB 충돌 없음. 포트만 다르면 uvicorn+Playwright 병렬 OK.

## 2. 순서 (의존성)

```
W0 (먼저, 단독)  ──머지──▶ feat/v2-redesign
                              │
        ┌─────────┬──────────┼──────────┬─────────┐  ← W0 머지 후 분기, 병렬
        W1        W2         W3         W4
        └─────────┴──────────┴──────────┘──머지──▶ feat/v2-redesign
                              │
                             W6 (펫일기 BE+FE) ──머지──▶ feat/v2-redesign
                              │
                             W5 (기록탭, W6 의존) ──머지──▶ feat/v2-redesign
```

## 3. 워크트리 셋업 / 머지 명령

```bash
# 0) 통합 브랜치
git switch -c feat/v2-redesign            # feature/demo-dummies에서

# 1) W0 워크트리 생성 → 그 폴더에서 claude 실행 → §4의 W0 /goal
git worktree add .claude/worktrees/v2-W0 -b feat/v2-W0-foundation feat/v2-redesign
#   (완료·확인 후) 통합에 머지:
git switch feat/v2-redesign && git merge --no-ff feat/v2-W0-foundation
git worktree remove .claude/worktrees/v2-W0

# 2) W1~W4 (W0 머지된 통합에서 분기, 병렬로 4개 터미널/세션)
git worktree add .claude/worktrees/v2-W1 -b feat/v2-W1-home-map feat/v2-redesign
git worktree add .claude/worktrees/v2-W2 -b feat/v2-W2-walking  feat/v2-redesign
git worktree add .claude/worktrees/v2-W3 -b feat/v2-W3-matching feat/v2-redesign
git worktree add .claude/worktrees/v2-W4 -b feat/v2-W4-camera   feat/v2-redesign
#   각 폴더에서 claude 실행 → 해당 /goal. 끝난 것부터 머지:
git switch feat/v2-redesign && git merge --no-ff feat/v2-W1-home-map   # W2·W3·W4 동일

# 3) W6 (W5보다 먼저)
git worktree add .claude/worktrees/v2-W6 -b feat/v2-W6-pet-diary feat/v2-redesign
git switch feat/v2-redesign && git merge --no-ff feat/v2-W6-pet-diary

# 4) W5 (W6 머지된 통합에서 분기)
git worktree add .claude/worktrees/v2-W5 -b feat/v2-W5-record-tab feat/v2-redesign
git switch feat/v2-redesign && git merge --no-ff feat/v2-W5-record-tab
```

> 각 워크트리에서 작업 시작 시 첫 줄 권장: `conda activate alpha-blip` 후 `claude` 실행.
> 충돌은 W0 설계(라우트 선등록+스텁+CSS 배너 append)로 사실상 0. 그래도 머지 전 `git merge feat/v2-redesign`로 통합 최신을 먼저 당겨오면 안전.

## 4. `/goal` 프롬프트 (각 워크트리에서 그대로 붙여넣기)

> 공통 전제(모든 프롬프트에 내포): 먼저 `docs/v2_redesign/00_orchestration.md`·`01_overview.md`·`docs/mvp_refactor/01_design_system.md`를 읽고 시작.
> Vanilla JS/ESM·빌드 없음·디자인 시스템 준수·**자기 담당 파일만 수정(공용 파일 금지)**·app.css 추가는 파일 끝 `/* === W{n} === */` 배너로만.

### W0 — 기반
```
/goal docs/v2_redesign/10_W0_foundation.md를 그 문서의 DoD대로 구현한다. 먼저 같은 폴더의 00_orchestration.md·01_overview.md와 docs/mvp_refactor/01_design_system.md를 읽는다. 범위: (a) index.html 탭바를 3탭(좌→우: 기록 #/diary / 홈 #/home / 마이 #/my, data-tab=diary/home/my)으로 교체 + icons.js에 map 등 신규 아이콘 추가, (b) app.js에 신규 라우트 7종 선등록(#/home→homeMapScreen·#/walk→walkingScreen·#/matching/:id→matchingScreen·#/camera→cameraScreen·#/diary→recordTabScreen·#/pet-diary/new→petDiaryNewScreen·#/pet-diary/:id→petDiaryViewScreen)하고 #/quest·#/record 라우트 제거, (c) screens/에 빈 스텁 6개(home_map·walking·matching·camera·record_tab·pet_diary, 스펙 §3.6 시그니처 고정), (d) ui.js에 centerModal 헬퍼, (e) store.js에 walkClips 키+addWalkClip/clearWalkClips, (f) my.js에서 업적·내 방 링크와 achievementsCard 제거(백엔드 무변경). 제약: Vanilla JS/ESM·빌드 없음·디자인 시스템 준수·app.css 추가는 끝에 /* === W0 === */ 배너로만. 완료 조건: PORT=9010 scripts/start.sh로 기동 후 Playwright 헤드리스(BASE=http://localhost:9010)로 (1) 가입→펫 등록 후 탭바 data-tab이 정확히 diary/home/my 3개이며 방/랭킹 탭 부재를 단언, (2) #/home·#/walk·#/matching/x·#/camera·#/diary·#/pet-diary/new 직접 이동 시 스텁 렌더+콘솔 에러 0, (3) 마이에 업적/내 방 링크 부재, (4) centerModal 1회 등장/닫힘을 단언한다. scripts/fe_smoke.py를 새 탭/홈 기준으로 수정해 통과시키고, 스크린샷 경로와 통과 로그를 보여준다. 또는 40턴 후 중단.
```

### W1 — 홈 지도
```
/goal docs/v2_redesign/11_W1_home_map.md를 그 문서의 DoD대로 구현한다. 먼저 00_orchestration.md·01_overview.md·docs/mvp_refactor/01_design_system.md를 읽는다. 담당 파일은 server/static/js/screens/home_map.js 하나만 채운다(공용 파일 수정 금지, CSS는 app.css 끝 /* === W1 === */ 배너로만). 핵심: 기존 walk.js 지도 레이어를 idle 모드로 재구성 — 오늘의퀘스트 배너 제거, 축척 확대+본인 중앙 빨강 마커, 주변은 강아지 캐릭터 핀만(이름/거리 칩 제거), 마커 탭 시 centerModal(프로필+CTA), 타 강아지[같이 산책하기]→본인 walk session 보장 후 POST /match-requests→#/matching/:id, 본인 강아지[산책하기]→walk session 시작+store.clearWalkClips→#/walk. 완료 조건: PORT=9011 scripts/start.sh 기동 후 Playwright 헤드리스(BASE=http://localhost:9011, 데모 컨텍스트)로 (1) #/home에 지도+본인 빨간 마커(중앙) 렌더+콘솔 에러 0(타일/WebGL 잡음 제외), (2) 주변 마커가 강아지 캐릭터만(메타 칩 없음)임을 단언, (3) 타 강아지 탭→centerModal→[같이 산책하기]→POST /match-requests 200→#/matching/:id 진입 단언, (4) 본인 마커 탭→[산책하기]→walk session 생성→#/walk 진입 단언. scripts/fe_smoke_walk.py의 홈/지도 부분을 새 구조로 수정해 통과시키고 before/after 스크린샷+로그를 보여준다. 또는 50턴 후 중단.
```

### W2 — 산책 중
```
/goal docs/v2_redesign/12_W2_walking.md를 그 문서의 DoD대로 구현한다. 먼저 00_orchestration.md·01_overview.md·docs/mvp_refactor/01_design_system.md를 읽는다. 담당 파일은 server/static/js/screens/walking.js 하나만(공용 파일 금지, CSS는 /* === W2 === */ 배너). 핵심: 활성 산책 지도 + 상단 투명 퀘스트박스(미션 ≤2, 지도 가림 없음, 탭→#/camera?mission=&quest=) + 좌하단 일반촬영(→#/camera) + 우하단 통화종료(phone-off). 진입 시 오늘 퀘스트 자동확보(없으면 candidates 1개 자동 select). 카메라 복귀 시 store.walkClips로 퀘스트 완료 갱신. 통화종료→매칭이면 match-session end·혼자면 walk end→POST /records(누적 clip_ids+daily_quest_id, visibility="diary", match면 match_session_id 혼자면 walk_session_id)→store.clearWalkClips·setWalkId(null)→#/diary?saved=1. 매칭 진입은 #/walk?match=<id>, 혼자는 #/walk. 완료 조건: PORT=9012 기동 후 Playwright(BASE=http://localhost:9012, 데모)로 (1) #/walk에 지도+상단 퀘스트박스(≤2, 지도 가림 없음)+좌하단 촬영+우하단 종료 렌더+콘솔 0, (2) 퀘스트박스 탭→#/camera?mission=...&quest=... 단언, 좌하단→#/camera(mission 없음) 단언, (3) 카메라 복귀(모킹) 후 해당 퀘스트 완료표시 단언, (4) 우하단 종료→end API+POST /records(누적 clip_ids 포함) 201→#/diary 진입+누적 클립 초기화 단언. fe_smoke_walk.py/fe_smoke_record.py 산책중 부분을 수정해 통과, 스크린샷+로그. 또는 60턴 후 중단.
```

### W3 — 산책 매칭중
```
/goal docs/v2_redesign/13_W3_matching.md를 그 문서의 DoD대로 구현한다. 먼저 00_orchestration.md·01_overview.md·docs/mvp_refactor/01_design_system.md를 읽는다. 담당 파일은 server/static/js/screens/matching.js 하나만(공용 파일 금지, CSS는 /* === W3 === */ 배너). 핵심: 라우트 #/matching/:id(=match_request_id), 진입 직후 GET /match-requests/:id 폴링(구 match.js requestWait 로직 이식, accepted→세션 확보·rejected/expired/cancelled→토스트+#/home). 지도엔 본인(빨강)+상대(강아지 핀) 둘만(nearby 폴링 안 함). 발자국 트래킹은 프론트 시뮬: 폴링 틱마다 직전 위치에 footprints 마커 누적(최근 N개만 유지, fade), 백엔드 변경 없음. 하단 [매칭 성공]→store.clearWalkClips→navigate(`/walk?match=<match_session_id>`). 데모 목업은 자동수락이라 바로 세션단계. 완료 조건: PORT=9013 기동 후 Playwright(BASE=http://localhost:9013, 데모)로 (1) W1에서 타 강아지[같이 산책하기]→#/matching/:id 진입, 본인+상대 둘만(주변 마커 없음) 단언+콘솔 0, (2) 폴링으로 발자국 마커가 누적(개수 증가) 단언, (3) 자동수락 세션확정→[매칭 성공]→#/walk?match=... 진입 단언, (4) 거절/만료 경로→토스트+#/home 복귀 단언. fe_smoke_walk.py 매칭 부분 수정해 통과, 스크린샷+로그. 또는 60턴 후 중단.
```

### W4 — 카메라(가로)
```
/goal docs/v2_redesign/14_W4_camera.md를 그 문서의 DoD대로 구현한다. 먼저 00_orchestration.md·01_overview.md·docs/mvp_refactor/01_design_system.md를 읽는다. 담당 파일은 server/static/js/screens/camera.js(+media.js 재사용, 변경 최소·필요시 /* W4 */ 주석). 공용 파일 금지, CSS는 /* === W4 === */ 배너. 핵심: 라우트 #/camera, setTab(null), 가로(landscape) 전체화면 카메라 프리뷰. 쿼리 ?quest=가 있으면 상단에 퀘스트 한 줄(이미지2의 "얼렁뚱땅…" 위치) 표기·없으면 미표기. 우상단 X→#/walk 취소복귀. 하단 촬영 버튼→media.js openCamera/record(2초 클립)→FormData(file,duration_ms,order,mission_id?)로 POST /clips/upload→store.addWalkClip({clip_id,mission_id,order})→토스트→#/walk 복귀. onLeave에서 stopStream. 완료 조건: PORT=9014 기동 후 Playwright(BASE=http://localhost:9014, fake 카메라)로 (1) #/camera?quest=테스트 진입→가로 레이아웃+상단 퀘스트 텍스트 표시 단언+콘솔 0, (2) #/camera(쿼리 없음)→퀘스트 텍스트 미표시 단언, (3) 촬영 버튼→POST /clips/upload 201→store.walkClips 길이 증가→#/walk 복귀 단언, (4) 퀘스트 진입 촬영 시 업로드 폼에 mission_id 포함 단언. fe_smoke_record.py 촬영 부분 수정해 통과, 스크린샷+로그. 또는 50턴 후 중단.
```

### W6 — 펫일기 (BE+FE) · **W5보다 먼저**
```
/goal docs/v2_redesign/16_W6_pet_diary.md를 그 문서의 DoD대로 구현한다. 먼저 00_orchestration.md·01_overview.md·docs/mvp_refactor/01_design_system.md를 읽는다. 범위(BE): server/models.py에 PetDiary(pet_diaries: id·user_id·pet_id?·diary_date·mood·activity_tags(JSON)·text?·created_at), server/schemas.py에 PetDiaryCreateReq/Out/ListRes, server/api/pet_diary.py 신설(POST /api/pet-diary·GET /api/pet-diary?from&to|?date·GET/{id}·PATCH/{id}·DELETE/{id}, 본인/owner 가드), server/main.py 라우터 등록. (FE): screens/pet_diary.js — #/pet-diary/new(기분 5단계+활동 칩 다중선택+텍스트→POST→#/diary), #/pet-diary/:id(상세/편집/삭제), 그리고 W5가 쓸 표시카드 petDiaryCard(d,{onClick}) export(이미지4 형태). 활동 카탈로그는 스펙 §3(날씨/사람/식사/이동) 사용, 아이콘은 Lucide(없으면 icons.js 추가). 제약: 디자인 시스템 칩/세그/입체버튼, 인라인 스타일 금지, CSS는 /* === W6 === */ 배너. 완료 조건: PORT=9016 기동 후 (1) pet_diaries 테이블 자동생성+POST/GET/PATCH/DELETE /api/pet-diary가 인증·owner 가드로 2xx 동작함을 curl로 보여주고, Playwright(BASE=http://localhost:9016)로 (2) #/pet-diary/new?date=오늘→기분 선택+활동 칩 다중선택+텍스트→저장 201→#/diary 이동 단언+콘솔 0, (3) 저장 후 GET /pet-diary?date=에 1건·#/pet-diary/:id 상세·편집·삭제 단언, (4) petDiaryCard가 이미지4 형태로 렌더되는지 단언. scripts/fe_smoke_petdiary.py를 신설해 통과시키고 스크린샷+로그. 또는 70턴 후 중단.
```

### W5 — 기록 탭 (+상대기록 API) · **W6 머지 후 분기**
```
/goal docs/v2_redesign/15_W5_record_tab.md를 그 문서의 DoD대로 구현한다(W6은 머지되어 있다고 가정; 통합 최신을 먼저 rebase). 먼저 00_orchestration.md·01_overview.md·docs/mvp_refactor/01_design_system.md를 읽는다. 담당 파일: server/static/js/screens/record_tab.js, server/api/matches.py(엔드포인트 추가), server/api/clips.py(권한), server/schemas.py(append). 핵심(FE): #/diary 재설계 — 상단 둥근 [기록] 칩→캘린더/공유 토글(캘린더=날짜 점프, 공유=비활성), 선택 날짜의 내 기록영상 + (매칭이면 신규 API로) 상대 기록영상 썸네일, 하단 펫일기 섹션(없으면 "일기가 없어요."+작성 진입, 있으면 W6의 petDiaryCard), 좌우 스와이프로 날짜 이동(영상+펫일기 동시 갱신), 방 버튼/공유옵션 없음. 핵심(BE): GET /api/match-sessions/{id}/records(참여자 전용, {mine:[clips],partner:[clips]}) 추가, clips.py stream 권한을 매칭 동행자가 상대의 해당 세션 클립을 볼 수 있게 확장(매칭 record 클립 한정). 제약: 디자인 시스템 준수, 인라인 스타일 금지, CSS는 /* === W5 === */ 배너. 완료 조건: PORT=9015 기동 후 Playwright(BASE=http://localhost:9015, 데모 매칭 산책 1회 수행)로 (1) #/diary에 [기록] 칩+영상 섹션+펫일기 섹션 렌더, 방 버튼/공유옵션 부재+콘솔 0, (2) [기록] 칩→캘린더/공유 토글, 캘린더로 날짜 선택→해당 날짜 이동 단언·공유 비활성 단언, (3) 매칭 산책 record에서 내 영상+상대 영상 썸네일 둘 다 표시(신규 API 200+상대 클립 stream 200), 혼자 산책은 상대 영역 미표시 단언, (4) 펫일기 0개→빈 상태/1개 이상→카드+상세 진입 단언, (5) 좌우 스와이프→날짜 변경 시 영상+펫일기 동시 갱신 단언. fe_smoke_record.py 기록탭 부분 수정해 통과, before/after 스크린샷+로그. 또는 70턴 후 중단.
```

## 5. 운영 팁

- **한 번에 하나 확인 후 진행 권장**: W0 끝나면 머지·확인 → 그다음 W1~W4 병렬. `/goal`은 평가기가 대화에 드러난 것만 판정하므로 범위가 클수록 표류 위험.
- **막히면** `/goal clear`로 멈추고 수동으로 한두 턴 잡아준 뒤 다시 `/goal`.
- **포트 충돌**: 반드시 워크트리별 지정 포트(§1) 사용. 같은 포트로 동시에 두 uvicorn 띄우지 않기.
- **머지 전 안전절차**: 각 워크트리에서 `git merge feat/v2-redesign`(통합 최신 당기기)로 충돌을 워크트리 안에서 먼저 해소.
- **스펙↔구현 차이**가 생기면 해당 `docs/v2_redesign/*.md`를 실제에 맞게 갱신하고 머지에 포함.
- (대안) 한 세션에서 내가 직접 오케스트레이션하길 원하면, Agent를 worktree 격리로 병렬 실행하는 방식도 가능. 다만 위 `/goal`-per-worktree가 중간 점검·롤백이 쉬움.
