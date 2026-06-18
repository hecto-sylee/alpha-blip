# 프로젝트 구조 & 실행

> [10_dev_stack.md](../mvp_planning/10_dev_stack.md)의 프로젝트 구조를 구현 가능한 수준으로 구체화한다.

---

## 디렉터리 스캐폴드

```
pet-matching-app/
├─ server/
│  ├─ main.py              # FastAPI 앱 생성, 라우터 등록, static mount, startup(seed)
│  ├─ database.py          # SQLAlchemy engine/session, create_all
│  ├─ models.py            # 전체 ORM 모델 (02_data_model.md)
│  ├─ schemas.py           # Pydantic 요청/응답 DTO
│  ├─ seed.py              # 퀘스트/미션 seed 적재 (06_quest_seed.md)
│  ├─ deps.py              # get_db, get_current_user(토큰)
│  ├─ utils/
│  │  ├─ geo.py            # Haversine 거리, 대략적 위치 오프셋
│  │  └─ codes.py          # 6자리 참여 코드 생성
│  ├─ api/
│  │  ├─ auth.py           # 게스트 세션
│  │  ├─ pets.py           # F-02
│  │  ├─ walks.py          # F-01 산책 세션 + 위치
│  │  ├─ nearby.py         # F-01 근처 강아지
│  │  ├─ matches.py        # F-03/04/05 요청·세션·로그
│  │  ├─ records.py        # F-10 기록
│  │  ├─ clips.py          # F-10 2초 클립 업로드/스트리밍
│  │  ├─ rooms.py          # F-11 방
│  │  ├─ quests.py         # F-12 퀘스트
│  │  ├─ reactions.py      # F-11 이모지 반응
│  │  └─ privacy.py        # F-09 차단/신고/설정
│  ├─ services/            # 도메인 로직 (라우터에서 분리)
│  │  ├─ matching.py       # 요청 충돌·만료·세션 생성
│  │  ├─ quest.py          # 후보 추천·선택·lock
│  │  └─ room.py           # 코드 발급·인원·중복 참여
│  ├─ static/
│  │  ├─ index.html        # SPA 진입 (단일 페이지)
│  │  ├─ css/app.css
│  │  └─ js/               # 04_frontend_spec.md 모듈 구조
│  └─ uploads/             # 업로드된 2초 클립(WebM) (gitignore)
│
├─ android/                # 05_android_and_demo.md — WebView 래퍼
│
├─ scripts/
│  ├─ start.sh             # uvicorn 실행
│  └─ tunnel.sh            # ngrok http 8000
│
├─ requirements.txt
├─ walk.db                 # SQLite (gitignore, 자동 생성)
└─ docs/
```

> `uploads/`, `walk.db`, `*.pyc`, `android/build/`, `.ngrok` 등은 `.gitignore`.

---

## 의존성 (`requirements.txt`)

```
fastapi
uvicorn[standard]
sqlalchemy>=2.0
pydantic>=2
python-multipart
aiofiles
```

> 외부 DB·ORM 마이그레이션 도구 불필요 (MVP는 `Base.metadata.create_all`).
> 프론트는 빌드 스텝 없음 — MapLibre는 CDN `<script>`로 로드.

---

## 실행

### 로컬 개발
```bash
pip install -r requirements.txt
uvicorn server.main:app --reload --host 0.0.0.0 --port 8000
# → http://localhost:8000  (SPA + API 동일 origin)
```

### 폰 시연 (ngrok)
```bash
ngrok http 8000
# → https://xxxx.ngrok-free.app 을 폰 브라우저 또는 Android 앱 서버주소로 사용
```

> getUserMedia / Geolocation 은 **HTTPS(또는 localhost)** 에서만 동작 → 폰 테스트는 ngrok HTTPS 필수.

---

## `main.py` 책임 (스켈레톤 지시)

1. `FastAPI()` 생성, CORS는 동일 origin이라 기본 불필요(앱/타 origin 테스트 시만 허용)
2. `@app.on_event("startup")`: `Base.metadata.create_all(engine)` + `seed.run()`
3. `app.include_router(...)` 로 `api/*` 등록 (prefix `/api`)
4. 업로드 정적: `/uploads`는 인증 스트리밍 라우트(`clips.py`)로만 노출 권장
5. SPA 서빙: `app.mount("/static", StaticFiles(...))` + `GET /` → `index.html`
6. SPA 라우팅은 클라이언트 사이드 → 알 수 없는 GET 경로는 `index.html` 폴백
