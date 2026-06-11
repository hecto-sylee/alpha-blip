# `/goal`로 mvp_spec 구현하기 — 사용 가이드 & 프롬프트 모음

> `/goal`은 **Claude Code 내장 명령** (v2.1.139, 2026-05-11 추가).
> 출처: [공식 /goal 문서](https://code.claude.com/docs/en/goal.md) · [commands](https://code.claude.com/docs/en/commands) · [changelog](https://code.claude.com/docs/en/changelog)
> 별도 설치/커스텀 명령 불필요. 현재 환경은 2.1.172라 바로 사용 가능.

---

## 0. 사용법 (문법)

| 입력 | 동작 |
|---|---|
| `/goal <완료 조건 텍스트>` | 그 조건이 충족될 때까지 여러 턴 자동 진행 |
| `/goal` (인자 없이) | 현재/최근 목표 상태 표시 |
| `/goal clear` | 목표 취소(중단). `stop`·`off`·`reset`·`none`·`cancel`도 동일 |

- 조건 텍스트는 **같은 줄에 인라인**으로 입력. 최대 4000자.
- **자동 진행**: 매 턴 종료 후 평가기(기본 Haiku)가 조건 충족 여부를 판정해 다음 턴을 띄움. 단계별 승인 없이 진행됨 → trust 모드 필요.
- **상한 설정**: 조건문 안에 `또는 N턴 후 중단` 같은 절을 넣어 한도를 건다(별도 플래그 없음).
- **종료**: 조건 충족 시 자동 종료(소요 시간·턴·토큰 기록) / `/goal clear` / `-p` 모드는 Ctrl+C.
- 세션을 `--resume`·`--continue`로 재개하면 활성 목표도 복원됨(타이머·턴 수는 리셋).

### 좋은 완료 조건 = 이렇게 쓴다 (공식 가이드)
평가기는 **도구를 직접 돌리지 못하고 대화에 드러난 내용만 판정**한다. 따라서 조건은 **Claude가 실행해서 결과를 대화에 남길 수 있는** 형태여야 한다.

| 요소 | 예 |
|---|---|
| 측정 가능한 끝 상태 | 테스트 통과, 빌드 exit 0, 파일 개수, 빈 큐 |
| 증명 방법 명시 | "`uvicorn`으로 띄워 `curl`이 2xx" 처럼 **Claude가 실행해 보여줄 것** |
| 지켜야 할 제약 | "다른 마일스톤 기능은 건드리지 않는다" |

> 나쁜 예: "M1을 잘 구현한다"(판정 불가). 좋은 예: "서버 기동 후 가입→등록→조회가 2xx임을 실행 로그로 보여준다".

---

## 1. 마일스톤별 완성 프롬프트 (복붙용)

> 각 프롬프트는 [00_implementation_plan.md](./00_implementation_plan.md)의 DoD를 **실행으로 증명 가능한 조건**으로 옮긴 것.
> 한 단계씩 끊어 실행하고 결과를 확인한 뒤 다음으로 넘어가는 걸 권장한다.

### M0 — 스캐폴드
```
/goal docs/mvp_spec를 따라 M0(스캐폴드)를 구현한다. 완료 조건: 01_project_structure.md의 디렉터리/파일 구조(server/main.py·database.py·models.py·static/index.html 등)가 생성되고, `pip install -r requirements.txt` 후 `uvicorn server.main:app`로 서버가 에러 없이 기동되어 GET / 가 SPA 셸 HTML을 200으로 반환함을 직접 실행해 로그로 보여준다. 또는 15턴 후 중단.
```

### M1 — 계정·프로필 (F-02)
```
/goal docs/mvp_spec를 따라 M1(계정·프로필)을 구현한다. 02_data_model의 users·pets, 03_api_spec의 Auth·Pets를 따른다. 완료 조건: 서버 기동 후 curl로 (1) POST /api/auth/guest 가 auth_token을 201로 발급, (2) POST /api/pets 가 201, (3) GET /api/pets/{id} 가 200, (4) PATCH /api/pets/{id} 가 200 임을 한 번에 실행해 응답 로그로 보여준다. 또는 25턴 후 중단.
```

### M2 — 산책·지도·매칭 (F-01/03/04/05)
```
/goal docs/mvp_spec를 따라 M2(산책·지도·매칭)를 구현한다. 03_api_spec의 Walks·Nearby·Matches를 따르고, 근처 검색은 앱 레벨 Haversine, 매칭 만료는 lazy 처리한다. 완료 조건: 게스트 사용자 A·B를 만들어 (1) 둘 다 POST /api/walks/start, (2) A의 GET /api/nearby/dogs 응답에 B가 대략적 위치로 표시, (3) A→B match-request → B accept → match-session 생성, (4) end 시 match-log 생성까지를 curl 스크립트로 한 번에 통과함을 실행 로그로 보여준다. 또는 35턴 후 중단.
```

### M3 — 기록·2초 클립·퀘스트 (F-10/12)
```
/goal docs/mvp_spec를 따라 M3(기록·2초 클립·퀘스트)를 구현한다. 02의 records·clips·quest_*·daily_quests, 03의 Records·Clips·Quests, 06의 seed를 따른다. 완료 조건: 서버 기동(startup seed 적재) 후 (1) GET /api/quests/candidates 가 후보 3개, (2) POST /api/quests/select 로 lock, (3) 더미 webm 파일로 POST /api/clips/upload 201, (4) POST /api/records 로 클립을 묶어 기록 저장 201, (5) GET /api/records 에 그 기록이 보임을 curl로 실행해 로그로 보여준다. 또는 35턴 후 중단.
```

### M4 — 방 (F-11)
```
/goal docs/mvp_spec를 따라 M4(방)를 구현한다. 02의 rooms·room_members·reactions, 03의 Rooms·Reactions를 따른다. 완료 조건: (1) 사용자 A가 POST /api/rooms 로 방+6자리 join_code 생성, (2) GET /api/rooms/code/{code} 조회, (3) 사용자 B가 POST /api/rooms/{id}/join, (4) B가 visibility=room 으로 POST /api/records, (5) A가 POST /api/reactions 로 그 기록에 이모지 토글, (6) GET /api/rooms/{id} 타임라인에 기록과 반응이 보임을 curl로 실행해 로그로 보여준다. 또는 35턴 후 중단.
```

### M5 — 설정·Android·시연 (F-09)
```
/goal docs/mvp_spec를 따라 M5(설정·Android·시연)를 구현한다. 완료 조건: (1) 03의 Privacy(block/unblock/report) 엔드포인트가 curl로 2xx 동작함을 보여주고, (2) 05_android_and_demo의 android/ WebView 프로젝트 파일(MainActivity.kt·AndroidManifest.xml 권한/cleartext/딥링크)과 scripts/start.sh·tunnel.sh를 생성한다. 실기기 ngrok 시연은 수동이므로 코드/설정 산출물 존재까지만 조건으로 한다. 또는 25턴 후 중단.
```

### (선택) M0~M2 한 번에
```
/goal docs/mvp_spec의 M0~M2를 구현한다. 완료 조건: 로컬에서 서버 기동 후, 게스트 가입→반려동물 등록→산책 시작→근처 표시→매칭 요청→수락→종료→매칭 로그까지를 curl 스크립트로 한 번에 통과함을 실행 로그로 보여준다. 또는 60턴 후 중단.
```

---

## 2. 운영 팁
- **한 단계씩**: 자동 진행은 중간 점검이 어렵다 → M0 실행 → 확인 → M1 … 권장.
- **막히면**: `/goal clear`로 멈추고, 수동으로 한두 턴 잡아준 뒤 다시 `/goal`.
- **권한**: `/goal`은 trust 모드에서만 동작(`disableAllHooks`면 비활성). 첫 실행 시 trust 대화 수락.
- **비대화 실행**: `claude -p "/goal <조건>"` 으로 한 번에 끝까지 돌릴 수도 있음.
- 명세를 고치면 `/goal` 결과물도 바뀐다 — "무엇을"은 전부 [docs/mvp_spec/](./)에 있다.

---

## 3. Claude CLI 업데이트 방법

> `/goal`은 2.1.139+에 있으므로 현재(2.1.172)는 업데이트 불필요. 아래는 향후 참고.

| 설치 방식 | 업데이트 명령 |
|---|---|
| 공용(모든 방식) | `claude update` |
| 네이티브 설치 | 기본 **자동 업데이트**(백그라운드, 재시작 시 적용) + 수동 `claude update` |
| npm 전역 | `npm install -g @anthropic-ai/claude-code@latest`  *(주의: `npm update -g`는 최신으로 안 갈 수 있음)* |
| Homebrew | `brew upgrade claude-code` (또는 `claude-code@latest`) |
| WinGet | `winget upgrade Anthropic.ClaudeCode` |
| apt/dnf/apk | `sudo apt update && sudo apt upgrade claude-code` 등 |

- 버전 확인: `claude --version`
- **재로그인 불필요** — 인증은 업데이트 후에도 유지됨.
- Homebrew/WinGet/npm은 자동 업데이트 안 함(수동). 네이티브 설치만 자동.

> 출처: [Claude Code Setup/Update](https://code.claude.com/docs/en/setup)
