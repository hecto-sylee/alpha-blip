# 실행 가이드 (blip MVP)

> 한 줄 요약: **FastAPI 서버 하나가 API + 웹 프론트(SPA) + 업로드를 모두 서빙**한다.
> 그래서 "프론트를 따로 실행"하는 단계는 없다 — 서버를 띄우고 그 주소에 접속하면 그게 프론트다.
> 안드로이드 앱은 그 주소(ngrok HTTPS)를 WebView로 감싸는 래퍼일 뿐이다.

```
┌─────────────────────────────────────────────┐
│  FastAPI (uvicorn, :8000)                     │
│   ├─ GET /            → 웹 SPA (index.html)   │  ← "프론트"는 여기서 같이 나온다
│   ├─ GET /api/*       → REST API              │
│   └─ /api/clips/*     → 2초 클립 업로드/스트림 │
└─────────────────────────────────────────────┘
        ▲                          ▲
        │ http://localhost:8000    │ https://xxxx.ngrok-free.app
   PC 브라우저                 폰 브라우저 / 안드로이드 WebView
                              (카메라·위치는 HTTPS 필수 → ngrok)
```

세 가지 구성요소의 관계:

| 구성요소 | 실제로 무엇인가 | 실행 방법 |
|---|---|---|
| 백엔드 | FastAPI 서버 (`server/`) | `uvicorn` 으로 기동 |
| **웹 프론트** | `server/static/` 의 SPA. **백엔드가 서빙** | 별도 실행 없음. 브라우저로 서버 주소 접속 |
| 안드로이드 | `android/` WebView 래퍼 | Android Studio로 빌드 → APK 설치 → 서버 URL 입력 |

---

## 0. 사전 준비

```bash
# 1) Python 환경 (이 프로젝트는 conda 환경 'alpha-blip' 사용)
conda activate alpha-blip
pip install -r requirements.txt        # 최초 1회

# 2) ngrok (폰/안드로이드 시연용 HTTPS 터널)
#    https://ngrok.com 가입 후 authtoken 등록 (최초 1회)
ngrok config add-authtoken <YOUR_TOKEN>
```

> 카메라(`getUserMedia`)·위치(`Geolocation`)는 **HTTPS 또는 localhost**에서만 동작한다.
> → PC는 `localhost`로 충분하지만, **폰·안드로이드는 ngrok HTTPS가 필수**.

---

## 1. 백엔드 실행

### 로컬 (PC에서 개발/테스트)
```bash
conda activate alpha-blip
./scripts/start.sh
# 또는
uvicorn server.main:app --reload --host 0.0.0.0 --port 8000
```
- 기동 시 자동으로 `walk.db`(SQLite) 테이블 생성 + 퀘스트 seed 적재.
- 확인: 브라우저에서 `http://localhost:8000` → SPA 셸이 뜨면 정상.
- 헬스체크: `curl http://localhost:8000/healthz` → `{"ok":true}`

### ngrok 터널 (폰/안드로이드 시연)
서버를 **켜둔 채로**, 새 터미널에서:
```bash
./scripts/tunnel.sh
# 또는
ngrok http 8000
```
출력되는 `Forwarding  https://xxxx.ngrok-free.app` 주소가 시연용 공개 URL이다.
이 주소를 폰 브라우저나 안드로이드 앱에 넣는다.

---

## 2. 웹 프론트 실행 — **따로 없음**

프론트는 빌드 스텝이 없는 Vanilla JS SPA이고, 백엔드가 그대로 서빙한다.
즉 위에서 서버를 띄운 순간 프론트도 같이 떠 있다.

| 접속 위치 | 주소 |
|---|---|
| PC 브라우저 | `http://localhost:8000` |
| 폰 브라우저 (앱 없이 즉시 시연) | `https://xxxx.ngrok-free.app` |

- 정적 파일 위치: `server/static/index.html`, `server/static/js/`, `server/static/css/`
- 파일을 고치면 새로고침만 하면 반영된다(번들러/빌드 불필요).
- 클라이언트 라우팅: 알 수 없는 GET 경로는 `index.html`로 폴백(SPA).
- 딥링크 합류: `/?join=<코드>` 로 접속하면 초대 코드를 인식한다.

> MapLibre 지도는 CDN `<script>`로 로드되므로 인터넷만 되면 동작한다.

---

## 3. 안드로이드 실행 (WebView 래퍼)

`android/`는 웹 SPA를 네이티브로 감싸 **카메라·마이크·위치 권한**을 부여하는 얇은 래퍼다.
(소스: `MainActivity.kt`, `SettingsActivity.kt`, `AndroidManifest.xml`)

### 빌드 & 설치
1. **Android Studio**에서 `android/` 폴더를 연다 (Gradle 동기화).
2. 폰을 USB로 연결(개발자 모드/USB 디버깅 ON) 하거나 에뮬레이터 준비.
3. **Run ▶** (또는 `Build > Build APK`).

CLI로 빌드하려면 (Android SDK + Gradle wrapper 필요):
```bash
cd android
./gradlew assembleDebug                 # 결과: app/build/outputs/apk/debug/app-debug.apk
# 설치
adb install -r app/build/outputs/apk/debug/app-debug.apk
```
> 참고: 이 저장소에는 Gradle wrapper 바이너리(`gradlew`/`gradle-wrapper.jar`)를 포함하지 않았다.
> Android Studio로 열면 자동 생성되며, CLI 빌드를 원하면 `gradle wrapper`로 한 번 생성하면 된다.

### 앱에서 서버 연결
1. 앱 첫 실행 시 카메라·마이크·위치 권한을 허용한다.
2. 서버 주소가 비어 있으면 **SettingsActivity**가 뜬다 →
   ngrok HTTPS URL(`https://xxxx.ngrok-free.app`)을 입력하고 **저장하고 열기**.
3. WebView가 해당 URL을 로딩한다. (메뉴 → "서버 설정"에서 언제든 변경)

### 딥링크로 방 합류
```
app://join/<room_code>
```
이 링크를 열면 앱이 실행되며 WebView를 `https://.../?join=<room_code>`로 로딩해
방 참여 코드를 전달한다. (`AndroidManifest.xml`의 `app://join` intent-filter)

---

## 4. 동작 검증 (스모크 테스트)

서버를 켠 상태에서 (기본 `BASE=http://localhost:8000`):

```bash
bash scripts/smoke.sh        # M0–M2: SPA 셸 · 게스트/펫 · 산책/nearby · 매칭
bash scripts/smoke_m34.sh    # M3–M4: 퀘스트 select/lock · 클립/기록 · 방/반응
bash scripts/smoke_m5.sh     # M5  : 차단/신고/차단해제 (Privacy)
```

ngrok 주소로 검증하려면:
```bash
BASE=https://xxxx.ngrok-free.app bash scripts/smoke.sh
```

---

## 5. 시연 플로우 (폰 2대)

```
1. 서버 기동       ./scripts/start.sh
2. 터널           ./scripts/tunnel.sh   → https://xxxx.ngrok-free.app
3. 접속
   - 경로 A: 폰 브라우저로 ngrok URL 접속 (앱 설치 없이 즉시)
   - 경로 B: APK 설치 → SettingsActivity에 ngrok URL 입력
4. 두 기기에서 게스트 가입 → 반려동물 등록 → 산책 시작
5. 지도에서 서로 보임 → 요청 → 수락 → 세션 → 종료 → 로그
6. 방: join_code 또는 app://join/{code} 공유로 합류 → 기록·반응
```

---

## 6. 자주 막히는 곳

| 증상 | 원인 / 해결 |
|---|---|
| 카메라·위치가 폰에서 안 됨 | HTTP로 접속함. **반드시 ngrok HTTPS**로 접속 (localhost 제외) |
| `Address already in use` | 이전 uvicorn이 떠 있음. `pkill -f "uvicorn server.main:app"` 후 재기동 |
| ngrok 경고 페이지가 먼저 뜸 | 무료 플랜의 1회성 안내. "Visit Site" 클릭 또는 유료 도메인 사용 |
| 안드로이드에서 흰 화면 | SettingsActivity에서 URL 오타/HTTP 여부 확인. 메뉴 → 새로고침 |
| 앱이 cleartext(HTTP) 거부 | Manifest `usesCleartextTraffic=true` 적용됨(로컬 시연 한정). ngrok HTTPS 권장 |
| DB를 초기화하고 싶음 | 서버 끄고 `rm walk.db` 후 재기동 (테이블·seed 재생성) |
