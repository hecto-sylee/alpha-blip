# MVP 구현 명세 — 개요 & 빌드 플랜

> 이 폴더(`mvp_spec/`)는 **실제로 코드를 어떻게 짤지**를 정의한다.
> 기획(무엇을·왜)은 [mvp_planning/](../mvp_planning/), 채택한 스택(무슨 기술로)은 [10_dev_stack.md](../mvp_planning/10_dev_stack.md)를 따른다.
> 본 명세는 그 위에서 **모듈·스키마·엔드포인트·화면 단위의 구현 지시**를 담는다.

---

## 0. 한 줄 목표

> FastAPI 단일 서버가 REST API + 정적 웹 SPA + 업로드 파일을 모두 서빙하고,
> ngrok 터널로 폰에서 바로 산책·매칭·2초 클립 기록·퀘스트·방 공유를 시연할 수 있게 만든다.

---

## 1. 스택 요약 (구현 기준)

| 영역 | 채택 | 비고 |
|---|---|---|
| 서버 | Python + FastAPI + Uvicorn | API · 정적 SPA · 업로드 단일 서버 |
| DB | SQLite + SQLAlchemy 2.0 | 단일 파일 `walk.db`, startup 시 테이블 생성 + seed |
| 검증 | Pydantic v2 | 요청/응답 DTO |
| 업로드 | python-multipart, aiofiles | 2초 WebM 클립 → `uploads/` |
| 프론트 | HTML/CSS/Vanilla JS SPA | 단일 `index.html` + 모듈 JS |
| 지도 | MapLibre GL JS + OSM | F-01 산책 지도 |
| 브라우저 API | MediaRecorder, getUserMedia, Geolocation, localStorage, Web Share | 촬영·위치·세션·공유 |
| 앱 | Android WebView (Kotlin) | ngrok URL 로딩 래퍼 |
| 시연 | ngrok + start script | HTTPS 터널 |

> 위치 반경 검색은 PostGIS 대신 **앱 레벨 거리 계산(Haversine)** 으로 구현한다. ([10_dev_stack 지도·위치 영역](../mvp_planning/10_dev_stack.md) 참고)

---

## 2. 구현 대상 기능 (MVP)

| F-# | 기능 | 시스템 | 명세 위치 |
|---|---|---|---|
| F-02 | 반려동물 프로필 | 공통 | [02 데이터](./02_data_model.md) `pets`, [03 API](./03_api_spec.md) Pets |
| F-09 | 개인정보 보호 설정 | 공통 | 03 API Privacy |
| F-01 | 실시간 산책 지도 | S1 | 03 API Walks/Nearby, [04 프론트](./04_frontend_spec.md) 지도 |
| F-03 | 같이 산책하기 요청 | S1 | 03 API Match Requests |
| F-04 | 매칭 세션 | S1 | 03 API Match Sessions |
| F-05 | 매칭 로그 | S1 | 03 API Match Logs |
| F-10 | 산책 기록(2초 클립) | S3 | 02 `records`/`clips`, 03 Records, 04 녹화 |
| F-11 | 방(Room) 공유 | S3 | 02 `rooms`/`room_members`/`reactions`, 03 Rooms |
| F-12 | 산책 퀘스트 | S3 | 02 `quest_*`/`daily_quests`, 03 Quests, [06 seed](./06_quest_seed.md) |

---

## 3. 빌드 마일스톤 (구현 순서)

각 마일스톤은 **폰(ngrok)에서 시연 가능**한 상태를 Definition of Done으로 한다.

| M | 범위 | 핵심 산출물 | 관련 화면 | DoD |
|---|---|---|---|---|
| **M0** | 스캐폴드 | FastAPI 서버, SQLite 연결, static SPA 셸, run 스크립트 | — | 서버 기동 + 빈 SPA가 브라우저에 뜬다 |
| **M1** | 계정·프로필 | guest 세션, `pets` CRUD | SCR-01·02·31 | 닉네임 가입 → 반려동물 등록 → 조회/수정 |
| **M2** | 산책·지도·매칭 | walk 세션, nearby(거리계산), MapLibre, 요청/세션/로그 | SCR-10~14 | 두 기기가 지도에서 서로 보이고 요청→수락→종료→로그 |
| **M3** | 기록·클립·퀘스트 | `records`/`clips`, 2초 MediaRecorder, 퀘스트 선택/lock/미션, 캘린더 | SCR-20·21·22·27 | 퀘스트 선택 → 2초 클립 촬영 → 기록 저장 → 다이어리 표시 |
| **M4** | 방 | `rooms`/멤버/참여코드, 방 기록 업로드, 이모지 반응, 방 퀘스트 | SCR-23~26 | 코드로 합류 → 방에 기록 공유 → 반응 |
| **M5** | 설정·앱·시연 | Privacy 설정, Android WebView, ngrok 배포 | SCR-30·32 | APK가 ngrok URL 로딩, 폰에서 카메라·위치 동작 |

> M2까지가 가설 1(매칭), M3까지가 가설 2(기록 루틴)의 최소 검증 지점. M4·M5는 공유·시연 강화.

---

## 4. 레이어 구조 (서버)

```
요청 → FastAPI router (api/*) → service (도메인 로직) → models (SQLAlchemy) → SQLite
                                      └ schemas (Pydantic) 로 입출력 검증
정적: GET / 및 /static/* → static/index.html + JS/CSS
미디어: POST /api/clips → uploads/ 저장, GET /api/clips/{id}/stream 반환
```

- **라우터는 얇게**, 비즈니스 규칙은 service에. (예: 퀘스트 lock, 방 인원 제한, 매칭 충돌 처리)
- 모든 핵심 행동은 `analytics_events`에 1줄 기록 (지표 검증용).

---

## 5. MVP 단순화 원칙 (구현 시 지킬 것)

| 항목 | MVP 구현 |
|---|---|
| 인증 | guest 토큰(닉네임 가입) + localStorage. 비밀번호/소셜 로그인은 후순위 |
| 실시간 | WebSocket 없음 → **폴링**(요청 수신/방 갱신은 2~5초 간격 조회) |
| 위치 | `watchPosition` 포그라운드. 반경 검색은 앱 레벨 Haversine |
| 대략적 위치 | 응답 시 좌표에 무작위 오프셋 적용 (정확 좌표 미저장/미노출) |
| 저장소 | DB=SQLite 파일, 미디어=`uploads/` 폴더 |
| 영상 | 2초 WebM. 길이 클라이언트에서 강제(자동 stop) |
| 퀘스트 | 사전 seed 데이터(06). LLM 생성은 범위 밖 |
| 수익화 | **범위 밖** (기획 결정) |

---

## 6. 문서 구성

| 문서 | 내용 |
|---|---|
| [00_implementation_plan.md](./00_implementation_plan.md) | 개요·빌드 플랜 (현재 문서) |
| [01_project_structure.md](./01_project_structure.md) | 디렉터리 스캐폴드·의존성·실행 |
| [02_data_model.md](./02_data_model.md) | SQLAlchemy/SQLite 스키마 |
| [03_api_spec.md](./03_api_spec.md) | FastAPI 엔드포인트 명세 |
| [04_frontend_spec.md](./04_frontend_spec.md) | SPA 구조·화면·브라우저 API |
| [05_android_and_demo.md](./05_android_and_demo.md) | Android WebView · ngrok 시연 |
| [06_quest_seed.md](./06_quest_seed.md) | 퀘스트/미션 seed 데이터 |
