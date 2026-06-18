# blip UI/UX 리팩토링 — 개요

> 이 폴더(`docs/mvp_refactor/`)는 **이미 구현·검증된 blip 프론트(`server/static/`)를 듀오링고풍으로 재설계**하기
> 위한 스펙·실행 문서다. 기능/플로우/백엔드는 그대로 두고 **비주얼 시스템 · 정보구조(IA) · 모션**만 바꾼다.
>
> 기존 방향 문서 `docs/mvp_planning/04_ui_ux_style.md`(글래스+M3 하이브리드)를 **이 리팩토링이 대체**한다.
> (해당 문서 상단에 "→ mvp_refactor로 이관" 주석을 R3에서 단다.)

---

## 0. 왜 (문제 정의)

현재 SPA는 동작하지만 다음이 불만:

1. **외곽 볼드 선** — 카드·입력·세그먼트·태그에 깔린 `1px/1.5px solid var(--outline)` 테두리가
   도처에 있어 각지고 밋밋한 인상.
2. **레이아웃/감도** — Liquid Glass + M3 하이브리드가 정적이고, "통통 튀는" 모션감이 부족.
3. **방(로그)이 묻혀 있음** — 방/로그가 `기록(diary)` 탭 아래에 중첩되어, snapchal처럼
   "쌓이는 로그가 한눈에" 들어오지 않는다.

## 1. 방향 (해결)

| 축 | 결정 |
|---|---|
| **비주얼** | 전체 **듀오링고풍 통일** — 글래스 레이어 제거, 챙키-입체(neo-tactile) 카드/버튼, **외곽 볼드 선 제거**(채움+솔리드 그림자로 분리) |
| **모션** | **CSS + Motion One**(ESM/CDN). Lottie는 보류. `prefers-reduced-motion` 전면 존중 |
| **하단 탭** | 3탭 → **4탭: 산책 / 방 / 기록 / 마이** (방 승격) |
| **방 탭** | 단순 방 목록 → **셋로그풍 세로 로그 피드**(쌓이는 로그 한눈에) + 방 필터 |
| **기록 탭** | 개인 다이어리 캘린더 **전용**(방과 분리) |
| **첫 화면** | **산책 홈** 유지 (핵심 루프 = 산책) |

> snapchal(`preview/snapchal/`) IA 참고: `오늘(로그 피드) / 촬영 / 공유`, 로그가 첫 화면.
> blip은 산책 루프가 핵심이라 첫 화면은 산책 홈을 유지하되, **방 탭을 로그 피드로 승격**해
> "쌓이는 로그" 경험을 전면화한다.

## 2. 스택 제약 (반드시 준수)

- **빌드 스텝 없는 Vanilla JS SPA.** 해시 라우팅, FastAPI가 `server/static/` 서빙.
- 모듈은 **ESM**(`app.js`가 `type="module"`). 모션 라이브러리는 **빌드 없이 ESM import**로만 추가.
  → React/Tailwind 컴포넌트(Magic UI·Animata 등)는 **도입 금지**(빌드 체인 필요, 철학 충돌).
  → 프레임워크 독립 + CDN/ESM 가능한 **Motion One**만 채택.
- 기존 모듈 구조(`api.js·store.js·router.js·polling.js·ui.js·screens/*`)·localStorage 키 유지.
- 백엔드 API는 그대로 사용(필요한 버그만 수정).

## 3. 영향 범위 (파일)

| 파일 | 변경 |
|---|---|
| `server/static/css/app.css` | 토큰·컴포넌트 전면 리스타일 (핵심) |
| `server/static/index.html` | 탭바 4탭화, Motion One import 자리 |
| `server/static/js/ui.js` | `mount/bottomSheet/celebrate`에 모션 훅인, `setTab` 그대로 |
| `server/static/js/motion.js` | **신설** — Motion One 래퍼(spring/stagger/inView, reduced-motion) |
| `server/static/js/screens/rooms.js` | 방 탭 → 로그 피드 개편, `setTab("diary")`→`setTab("room")` |
| `server/static/js/screens/room_view.js` | `setTab("diary")`→`setTab("room")` |
| `server/static/js/screens/{home,quest,diary,record,...}.js` | 화면별 모션 폴리시(최소 수정) |
| `scripts/fe_smoke*.py` | IA/셀렉터 변경에 맞춰 스모크 러너 수정 |

## 4. 문서 구성

| 문서 | 내용 |
|---|---|
| `00_refactor_overview.md` | (이 문서) 왜·무엇·범위 |
| `01_design_system.md` | 듀오링고풍 토큰·컴포넌트 스펙 (글래스 제거, 입체 버튼/카드) |
| `02_information_architecture.md` | 4탭 IA, 방 로그 피드, 라우팅/`setTab` 변경 |
| `03_motion_spec.md` | Motion One + CSS, `motion.js` 헬퍼, 순간별 모션 표, reduced-motion |
| `04_goals.md` | 실행 단위(R0~R4) **복붙용 /goal 프롬프트** (DoD = Playwright 헤드리스 증명) |
| `05_demo_mode.md` | (부가) 홈 test 키 → 1인 풀플로우(산책·매칭·기록·방공유) 데모 모드 스펙 |

## 5. 검증 원칙 (모든 goal 공통)

기존 프론트 goal과 동일하게 **정적 200 체크 금지**. 각 goal의 DoD는
**헤드리스 브라우저(Playwright Chromium)로 실제 화면을 클릭/입력해 플로우 통과 +
콘솔 에러 0 + before/after 스크린샷 + 실행 로그**로 증명한다.
재설계가 기존 `scripts/fe_smoke*.py`의 셀렉터/플로우를 깨면 **스모크 러너도 함께 수정**한다.
