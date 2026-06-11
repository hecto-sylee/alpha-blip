# MVP 개발 스택 & 개발 프로세스

> 이 문서는 **실제 MVP를 빠르게 만들어 모바일 실기기로 시연**하기까지의 구체적 구현 방식을 정의한다.
> 검증된 스냅챌(SnapChal) 프로토타입의 빌드/배포 방식을 그대로 차용한다.
> 단계별 기술 비전(Next.js·Supabase 등 확장 로드맵)은 [dev/01_tech_stack.md](../dev/01_tech_stack.md) 참고.
> 본 문서는 그 로드맵 이전에, **단일 서버 + 웹 SPA + WebView 래퍼 + ngrok 시연**으로 핵심 가설을 가장 빠르게 검증하는 실전 방식이다.

---

## 이 방식을 택한 이유

| 이유 | 설명 |
|---|---|
| 인프라 0 | FastAPI 단일 서버가 API + 정적 SPA + 업로드 파일을 모두 서빙. 별도 인프라/계정 없이 시작 |
| 단일 origin | 웹 SPA를 같은 서버에서 서빙 → CORS·배포 복잡도 제거 |
| 실기기 즉시 시연 | ngrok 터널 하나로 외부 HTTPS URL 발급 → 폰에서 바로 접속/촬영/위치 테스트 |
| 네이티브 기능 확보 | Android WebView 래퍼로 카메라·마이크·위치 권한, 파일 선택, 딥링크를 네이티브로 처리 |
| 빠른 반복 | SQLite 로컬 DB + startup seed로 스키마/콘텐츠를 코드와 함께 버전 관리 |

> 핵심: **"앱처럼 보이는 웹"을 단일 서버로 만들고, ngrok으로 실기기 시연한다.** 가설 검증 속도가 최우선.

---

## 전체 기술 스택

| 영역 | 사용 기술 | 역할 |
|---|---|---|
| Backend | Python | 서버 애플리케이션 언어 |
| API Framework | FastAPI | REST API, 파일 업로드, 정적 파일 서빙 |
| ASGI Server | Uvicorn | FastAPI 실행 서버 |
| ORM | SQLAlchemy | DB 모델/쿼리 |
| DB | SQLite | 로컬 단일 파일 DB (예: `walk.db`, 서비스명 미정) |
| Validation | Pydantic | API 요청/응답 DTO |
| File Upload | python-multipart, aiofiles | 2초 영상 클립(WebM) 업로드 처리 |
| Frontend Web | HTML / CSS / Vanilla JS | 모바일형 SPA UI (단일 `index.html`) |
| 지도 | MapLibre GL JS + OpenStreetMap | S1 실시간 산책 지도 (스냅챌엔 없던 추가 영역, 상세 기획은 아래 참고) |
| Browser APIs | MediaRecorder, getUserMedia, Geolocation, localStorage, Web Share API | 촬영·녹화·위치 수집·세션 저장·공유 |
| Android | Kotlin | 네이티브 APK 래퍼 |
| Android UI | AppCompat, Material, ConstraintLayout | 기본 화면/설정 UI |
| Android Web | Android WebView, AndroidX WebKit | 웹 SPA 로딩 |
| Build | Gradle, Android Gradle Plugin | Android 빌드 |
| 배포/시연 | ngrok, start script | 외부 모바일 접속용 터널링 |

> 스냅챌 대비 유일한 추가 영역은 **지도(S1 실시간 산책 매칭)** 다. 나머지(서버·DB·SPA·WebView·시연)는 동일 방식을 그대로 적용한다.

### 지도·위치 영역 — 기획 출처

이 문서는 **구현 스택**만 다루고, 지도·위치·매칭의 상세 기획·원칙은 아래 문서를 따른다. 본 문서는 그것을 어떤 기술로 구현할지만 정의한다.

| 영역 | 기획 출처 | MVP 구현 방식 |
|---|---|---|
| 실시간 산책 지도 (F-01) | [whole_planning/02-1 위치·지도 서비스](../whole_planning/02-1_location_service.md) · [mvp_planning/01_feature_spec F-01](./01_feature_spec.md) | MapLibre GL JS + OSM 타일, 내 위치/근처 마커 |
| 위치 수집·업데이트 | 위 02-1 + [개인정보 설정 F-09](./01_feature_spec.md) | Browser Geolocation `watchPosition` (포그라운드, HTTPS 필수) |
| 대략적 위치 표시 | 02-1 "정확한 좌표 미노출" 원칙 | 실제 좌표에 무작위 오프셋 적용해 반경 내 표시 ([dev/03_api_spec](../dev/03_api_spec.md) `/nearby/dogs` 참고) |
| 근처 강아지 반경 검색 (F-03 진입) | [whole_planning/02-3 매칭 서비스](../whole_planning/02-3_matching_service.md) | SQLite 단계에선 **앱 레벨 거리 계산**(Haversine), 정식 전환 시 PostGIS 반경 검색 |
| 매칭 요청·세션·로그 | 02-3 매칭 서비스 + [01_feature_spec F-03~F-05](./01_feature_spec.md) | FastAPI REST + 폴링 (정식 전환 시 Realtime/WebSocket) |
| 반려동물 프로필 | [whole_planning/02-2 프로필 서비스](../whole_planning/02-2_profile_service.md) | 동일 스키마를 SQLAlchemy 모델로 구현 |

> 즉 지도/위치/매칭의 **무엇을**은 whole_planning 서비스 문서가, **어떻게**는 본 문서가 담당한다.

---

## 프로젝트 구조

| 경로 | 내용 |
|---|---|
| `server/main.py` | FastAPI 서버, API 엔드포인트, 정적 SPA 서빙 |
| `server/models.py` | SQLAlchemy DB 모델 |
| `server/database.py` | SQLite 연결 설정, startup 시 테이블 생성 |
| `server/quest_data.py` | 산책 퀘스트 / 미션 seed 데이터 |
| `server/static/index.html` | 실제 웹 앱 UI/JS (모바일 SPA) |
| `server/uploads/` | 업로드된 2초 클립(WebM) 저장 |
| `android/` | Android WebView APK 프로젝트 |
| `docs/` | 기획·개발 문서 |

> DB 스키마는 [dev/02_data_model.md](../dev/02_data_model.md), API 명세는 [dev/03_api_spec.md](../dev/03_api_spec.md)를 따른다.
> 단, MVP 단계에서는 Supabase/PostgreSQL 대신 **SQLAlchemy + SQLite**로 동일 스키마를 구현한다. (PostGIS 반경 검색은 SQLite 단계에서 애플리케이션 레벨 거리 계산으로 대체)

---

## 서버 구성 원칙

| 원칙 | 내용 |
|---|---|
| 단일 서버 | FastAPI 하나가 API · 정적 SPA · 업로드 파일을 모두 서빙 |
| 인증 단순화 | 시연 단계는 별도 로그인 없이 계정/세션을 localStorage로 유지 (정식 단계에서 Supabase Auth/JWT로 전환) |
| 로컬 저장소 | DB는 SQLite 파일, 미디어는 `uploads/` 폴더 (정식 단계에서 Storage/S3로 전환) |
| 실시간성 | MVP는 WebSocket 없이 조회/폴링 기반 (정식 단계에서 Realtime/WebSocket으로 전환) |
| seed 적재 | 서버 startup 시 산책 퀘스트·미션 seed 데이터 적재 (안정성 우선, 사전 제작 콘텐츠) |
| 영상 포맷 | 2초 클립을 WebM 중심으로 처리 |

---

## Android WebView 래퍼

웹 SPA를 그대로 감싸 **네이티브 기능과 앱 배포 형태**를 확보한다.

| 기능 | 설명 |
|---|---|
| WebView 앱 | 서버의 웹 SPA를 Android 앱 안에서 실행 |
| 서버 주소 설정 | ngrok URL 등 외부 서버 주소를 SharedPreferences에 저장 |
| 카메라/마이크/위치 권한 | WebView 내 촬영·위치 수집을 위한 런타임 권한 요청 |
| 파일 선택 처리 | WebChromeClient 파일 chooser 지원 |
| 딥링크 | `app://join/{room_code}` 형태 방 초대 링크 처리 (스킴명 미정) |
| 새로고침/설정 메뉴 | 앱 메뉴에서 reload, server settings 제공 |
| Cleartext 허용 | 로컬/HTTP 서버 접속 가능하도록 설정 (시연 한정) |

---

## 개발 → 배포(시연) 프로세스

```
1. 로컬 개발
   FastAPI 서버 실행 (uvicorn) → SQLite 자동 생성 → startup seed(퀘스트/미션) 적재
   웹 SPA(static/index.html)를 같은 서버가 서빙 → 브라우저에서 개발/디버깅

2. 모바일 실기기 노출
   ngrok 으로 로컬 서버를 외부 HTTPS URL로 터널링
   → getUserMedia / Geolocation 은 HTTPS 컨텍스트에서만 동작하므로 ngrok HTTPS 필수

3. 두 가지 시연 경로
   (A) 모바일 브라우저로 ngrok URL 직접 접속
   (B) Android WebView APK 설치 → 앱이 ngrok URL 로딩
       → 카메라/마이크/위치 권한·파일 선택·딥링크를 네이티브로 처리

4. 방 초대/참여
   방 참여 코드 또는 app://join/{room_code} 딥링크로 외부 공유 → 즉시 합류
```

### 시연 체크리스트

| 항목 | 확인 |
|---|---|
| HTTPS 컨텍스트 | ngrok HTTPS URL 사용 (카메라·위치 권한 필수 조건) |
| 권한 허용 | 카메라·마이크·위치 권한 1회 허용 흐름 |
| 2초 클립 업로드 | MediaRecorder 녹화 → FormData 업로드 → 재생 확인 |
| 위치 표시 | Geolocation `watchPosition` → 지도 마커 갱신 |
| 방 참여 | 참여 코드/딥링크로 다른 기기에서 합류 |

---

## 정식 서비스 전환 매핑

MVP 검증 후 [dev/01_tech_stack.md](../dev/01_tech_stack.md)의 Phase 2~3 스택으로 점진 전환한다.

| MVP (본 문서) | 정식 전환 |
|---|---|
| SQLite | Supabase PostgreSQL / PostgreSQL + PostGIS |
| 앱 레벨 거리 계산 | PostGIS 반경 검색 (GIST 인덱스) |
| 폴링 / 조회 기반 | Supabase Realtime / WebSocket |
| localStorage 세션 | Supabase Auth / JWT |
| `uploads/` 폴더 | Supabase Storage / S3 / R2 |
| ngrok 시연 | Vercel/Netlify(웹) · TestFlight/Play Internal(앱) |
| Android WebView 래퍼 | React Native / Flutter 네이티브 앱 |

> MVP는 **검증 속도**, 정식은 **확장성·실시간성**. 본 문서 방식으로 가설을 검증한 뒤, 검증된 화면·데이터 모델을 정식 스택으로 옮긴다.
