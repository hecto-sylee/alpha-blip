# 스냅챌 (SnapChal) MVP

> 퀘스트 기반 하루 2초 영상 로그 소셜 앱  
> 알파팀 내부 시연용 · Python FastAPI + Android WebView

---

## 전체 구조

```
snapchal/
├── server/          ← Python FastAPI 백엔드 (여기서 실행)
│   ├── main.py
│   ├── models.py
│   ├── quest_data.py
│   ├── static/
│   │   └── index.html   ← 모바일 웹 프론트엔드 (전체 UI)
│   ├── uploads/         ← 영상 저장 폴더 (자동 생성)
│   └── start_server.bat / start_server.sh
└── android/         ← Android APK 프로젝트 (Android Studio로 빌드)
```

---

## STEP 1. 서버 실행

### Windows
```
cd snapchal/server
start_server.bat
```

### Mac / Linux
```bash
cd snapchal/server
chmod +x start_server.sh
./start_server.sh
```

서버가 뜨면 브라우저에서 **http://localhost:8000** 으로 접속해 확인합니다.

---

## STEP 2. ngrok으로 외부 접속 열기

> 핸드폰에서 접속하려면 ngrok이 필요합니다.

### ngrok 설치 (처음 1회)
1. https://ngrok.com 가입 후 authtoken 발급
2. 설치: https://ngrok.com/download

### ngrok 실행
```bash
ngrok http 8000
```

터미널에 나오는 URL 복사:
```
Forwarding   https://xxxx-xxxx.ngrok-free.app -> http://localhost:8000
```
이 URL을 APK 설정에 입력합니다.

---

## STEP 3. APK 빌드 및 설치

### 방법 A: Android Studio 사용 (권장)

1. Android Studio 설치: https://developer.android.com/studio
2. `snapchal/android` 폴더를 Android Studio로 열기
3. 상단 **Build → Build Bundle(s)/APK(s) → Build APK(s)** 클릭
4. 빌드 완료 후 `app/build/outputs/apk/debug/app-debug.apk` 생성
5. 핸드폰에 APK 전송 후 설치

### 방법 B: 명령줄 빌드
```bash
cd snapchal/android
./gradlew assembleRelease
# APK 위치: app/build/outputs/apk/release/app-release.apk
```

### APK 설치 방법
1. APK 파일을 카카오톡/메일로 전송
2. 핸드폰에서 파일 열기
3. "알 수 없는 앱 설치 허용" 후 설치

---

## STEP 4. 앱에서 서버 연결

1. 앱 실행
2. 우측 상단 메뉴 → **서버 주소 설정**
3. ngrok URL 입력: `https://xxxx.ngrok-free.app`
4. **저장 및 연결** 탭

---

## 시연 순서 (3명 기준)

```
A가 앱 실행 → 방 만들기 → 친구 모드 → 이름 입력 → 방 생성
  ↓
참여 코드 공유 (B, C에게)
  ↓
B, C가 앱 실행 → 참여 코드 입력 → 이름 입력 → 참여
  ↓
A가 오늘 로그 진입 (첫 접근자) → 퀘스트 3개 중 선택
  ↓
A, B, C 각각 현재 시간대 탭 클릭 → 미션 확인 → 탭 → 2초 촬영
  ↓
로그 화면에서 세 명의 영상 확인 → 이모지 반응
  ↓
저장/공유 버튼으로 공유
```

---

## 핵심 API 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | /api/rooms | 방 만들기 |
| GET | /api/rooms/code/{code} | 코드로 방 조회 |
| POST | /api/rooms/{id}/join | 방 참여 |
| GET | /api/rooms/{id}/today | 오늘 퀘스트 상태 |
| GET | /api/rooms/{id}/quest-candidates | 퀘스트 후보 3개 |
| POST | /api/rooms/{id}/quest | 퀘스트 선택 |
| GET | /api/rooms/{id}/mission/{hour} | 시간대 미션 |
| GET | /api/rooms/{id}/logs/{date} | 날짜별 로그 |
| POST | /api/videos/upload | 영상 업로드 |
| POST | /api/reactions | 이모지 반응 |
| DELETE | /api/videos/{id} | 영상 삭제 |
| POST | /api/rooms/{id}/leave | 방 나가기 |
| GET | /api/admin/quests | 퀘스트 관리 (숨김) |

---

## 퀘스트 목록

### 친구 모드 (6개)
- FQ-001 무지개 로그
- FQ-002 같은 포즈 챌린지
- FQ-003 내 주변 가장 웃긴 거
- FQ-004 공통 주제 로그
- FQ-005 우리는 하나 컨셉
- FQ-006 금지 장면 게임

### 커플 모드 (6개)
- CQ-001 같은 하루 다른 시선
- CQ-002 서로에게 보내는 순간
- CQ-003 취향 교환 로그
- CQ-004 만나는 날 로그
- CQ-005 서로 따라하기
- CQ-006 오늘의 마음 날씨

각 퀘스트는 06:00 ~ 23:00까지 18개 시간대별 미션을 포함합니다.

---

## 주의사항

- MVP는 로컬 서버 기반으로 시연합니다
- 영상은 서버의 `uploads/` 폴더에 저장됩니다
- 앱을 삭제하면 기기 ID가 초기화되어 방에 다시 참여해야 합니다
- 최대 5명까지 같은 방에 참여 가능합니다 (시연: 3명 기준)
