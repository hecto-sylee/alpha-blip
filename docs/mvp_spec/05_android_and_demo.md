# Android WebView 래퍼 & 배포(시연)

> 웹 SPA를 그대로 감싸 네이티브 권한·앱 배포 형태를 확보하고, ngrok으로 폰 실기기 시연한다.
> [10_dev_stack.md](../mvp_planning/10_dev_stack.md)의 Android/시연 항목 구현 지시.

---

## Android WebView 앱

### 구성
```
android/
├─ app/src/main/
│  ├─ java/.../MainActivity.kt      # WebView 호스트
│  ├─ java/.../SettingsActivity.kt  # 서버 URL 입력
│  ├─ res/layout/                   # 화면(ConstraintLayout)
│  └─ AndroidManifest.xml           # 권한 + cleartext + 딥링크
└─ build.gradle                     # AGP, Kotlin plugin
```

### 구현 요구사항

| 항목 | 구현 |
|---|---|
| WebView 설정 | `javaScriptEnabled`, `domStorageEnabled`(localStorage), `mediaPlaybackRequiresUserGesture=false` |
| 서버 주소 | `SharedPreferences`에 ngrok URL 저장 → WebView `loadUrl` |
| 카메라/마이크 권한 | `WebChromeClient.onPermissionRequest` → `grant()` (런타임 권한 선요청) |
| 위치 권한 | `onGeolocationPermissionsShowPrompt` → allow + `ACCESS_FINE_LOCATION` 런타임 |
| 파일 선택 | `WebChromeClient.onShowFileChooser` |
| 딥링크 | `app://join/{room_code}` intent-filter → WebView에 코드 전달(방 참여) |
| 메뉴 | reload / server settings |
| Cleartext | `usesCleartextTraffic=true`(로컬/HTTP 시연 한정) |

### Manifest 권한
```
INTERNET, ACCESS_FINE_LOCATION, CAMERA, RECORD_AUDIO
```

> 핵심: getUserMedia/Geolocation은 WebView에서도 **HTTPS(ngrok) + 권한 grant** 둘 다 충족해야 동작.

---

## 배포 → 시연 플로우

```
1. 서버 기동      uvicorn server.main:app --host 0.0.0.0 --port 8000
2. 터널          ngrok http 8000  →  https://xxxx.ngrok-free.app
3. 시연 경로 A    폰 브라우저로 ngrok URL 접속 (앱 없이 즉시)
   시연 경로 B    APK 설치 → SettingsActivity에 ngrok URL 입력 → WebView 로딩
4. 방 합류        join_code 또는 app://join/{code} 공유 → 다른 기기 합류
```

### `scripts/start.sh` / `scripts/tunnel.sh`
```bash
# start.sh
uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
# tunnel.sh
ngrok http 8000
```

---

## 시연 체크리스트

| 항목 | 확인 |
|---|---|
| HTTPS 컨텍스트 | ngrok HTTPS URL 사용 (카메라·위치 필수 조건) |
| 권한 1회 허용 | 카메라·마이크·위치 grant 흐름 정상 |
| 2초 클립 | 녹화→업로드→스트리밍 재생 OK |
| 위치/지도 | `watchPosition`→마커 갱신, nearby 표시 OK |
| 매칭 | 두 기기 요청→수락→세션→종료→로그 |
| 방 | 코드/딥링크 합류, 기록 공유, 반응 |
| 퀘스트 | 후보→선택(lock)→미션 클립→기록 연결 |

---

## 정식 전환 (참고)
MVP 검증 후 [dev/01_tech_stack.md](../dev/01_tech_stack.md) Phase 2~3로:
WebView 래퍼 → RN/Flutter 네이티브, SQLite → PostgreSQL/PostGIS, 폴링 → Realtime/WebSocket, ngrok → Vercel/TestFlight/Play.
