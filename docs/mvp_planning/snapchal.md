현재 코드 기준 **“스냅챌(SnapChal) MVP”**

구성: **Python FastAPI 서버 + SQLite DB + 정적 Web SPA + Android WebView 앱**

**전체 기술 스택**

| 영역 | 사용 기술 | 현재 역할 |
| --- | --- | --- |
| Backend | Python | 서버 애플리케이션 언어 |
| API Framework | FastAPI `0.111.0` | REST API, 파일 업로드, 정적 파일 서빙 |
| ASGI Server | Uvicorn `0.30.1` | FastAPI 실행 서버 |
| ORM | SQLAlchemy `2.0.30` | DB 모델/쿼리 |
| DB | SQLite | `snapchal.db` 로컬 DB |
| Validation | Pydantic `2.7.1` | API 요청 DTO |
| File Upload | python-multipart, aiofiles | WebM 영상 업로드 처리 |
| Frontend Web | HTML/CSS/Vanilla JS | 모바일형 SPA UI |
| Browser APIs | MediaRecorder, getUserMedia, localStorage, Web Share API | 촬영, 녹화, 세션 저장, 공유 |
| Android | Kotlin | 네이티브 APK 래퍼 |
| Android UI | AppCompat, Material, ConstraintLayout | 기본 화면/설정 UI |
| Android Web | Android WebView, AndroidX WebKit | 웹 앱 로딩 |
| Build | Gradle, Android Gradle Plugin `8.1.4` | Android 빌드 |
| Kotlin | Kotlin Android Plugin `1.9.20` | Android 코드 작성 |
| 배포/시연 | ngrok, start script | 외부 모바일 접속용 터널링 |

**프로젝트 구조**

| 경로 | 내용 |
| --- | --- |
| `snapchal/server/main.py` | FastAPI 서버, API 엔드포인트, 정적 SPA 서빙 |
| `snapchal/server/models.py` | SQLAlchemy DB 모델 |
| `snapchal/server/database.py` | SQLite 연결 설정 |
| `snapchal/server/quest_data.py` | 퀘스트/시간대별 미션 seed 데이터 |
| `snapchal/server/static/index.html` | 실제 웹 앱 UI/JS |
| `snapchal/server/uploads/` | 업로드된 WebM 영상 저장 |
| `snapchal/android/` | Android WebView APK 프로젝트 |
| `docs/` | 요구사항, MVP 범위, 화면 흐름, 시나리오 문서 |

**Backend 기능**

| 기능 | 설명 |
| --- | --- |
| 방 생성 | 방 이름, 모드, 사용자 이름, device_id 기반으로 방 생성 |
| 참여 코드 생성 | 6자리 랜덤 참여 코드 발급 |
| 방 참여 | 참여 코드로 방 조회 후 참여 |
| 중복 참여 방지 | 같은 device_id가 이미 참여 중이면 기존 participant 반환 |
| 최대 인원 제한 | 기본 최대 5명 |
| 방 나가기 | 참여자 상태를 `left`로 변경 |
| 빈 방 삭제 처리 | 모든 참여자가 나가면 방 상태를 `deleted` 처리 |
| 오늘의 로그 생성 | 날짜별 DailyLog 생성/조회 |
| 퀘스트 후보 추천 | 모드별 퀘스트 중 랜덤 3개 제공 |
| 오늘의 퀘스트 선택 | 하루 1개 퀘스트 선택 후 lock |
| 시간대 미션 조회 | `06:00~23:00` 시간 슬롯별 미션 제공 |
| 영상 업로드 | 시간대별 2초 영상 WebM 업로드 |
| 영상 스트리밍 | 업로드된 영상 파일 반환 |
| 영상 삭제 | 오늘 업로드한 본인 영상만 공유 로그에서 숨김 |
| 이모지 반응 | 영상 클립에 반응 추가 |
| 저장/공유 기록 | 저장 또는 공유 액션 기록 |
| 관리자 퀘스트 조회 | 전체 퀘스트/미션 조회 |
| 관리자 퀘스트 수정 | 제목, 설명, 활성화 여부 수정 |
| 이벤트 로깅 | 방 생성, 참여, 퀘스트 선택, 업로드, 반응 등 분석 이벤트 저장 |

**DB 모델**

| 테이블/모델 | 역할 |
| --- | --- |
| `Room` | 방 정보, 모드, 참여 코드, 상태 |
| `Participant` | 참여자, device_id, 표시 이름, 참여 상태 |
| `DailyLog` | 날짜별 로그 |
| `QuestTemplate` | 사전 제작 퀘스트 템플릿 |
| `QuestMissionTemplate` | 퀘스트별 시간대 미션 |
| `DailyQuest` | 특정 날짜에 선택된 퀘스트 |
| `VideoClip` | 업로드 영상, 시간 슬롯, 상태 |
| `Reaction` | 영상별 이모지 반응 |
| `ShareRecord` | 저장/공유 기록 |
| `AnalyticsEvent` | 사용자 행동 이벤트 로그 |

**Frontend/Web 기능**

| 화면/기능 | 설명 |
| --- | --- |
| 시작 화면 | 방 만들기 / 참여 코드 입력 |
| 방 만들기 | 친구 모드, 커플 모드 선택 |
| 초대 화면 | 참여 코드 복사, 초대 링크 공유 |
| 참여 화면 | 코드 입력 후 방 참여 |
| 로그 화면 | 참여자별/시간대별 영상 로그 보기 |
| 퀘스트 선택 | 후보 3개 중 오늘의 퀘스트 선택 |
| 미션 화면 | 현재 시간대 미션 안내 |
| 카메라 화면 | WebRTC 카메라/마이크 접근 |
| 녹화 | MediaRecorder 기반 WebM 녹화 |
| 업로드 | FormData로 서버 업로드 |
| 영상 재생 | 업로드된 로그 영상 재생 |
| 삭제 | 본인 오늘 영상 삭제 |
| 리액션 | ❤️ 😂 🔥 👍 😮 반응 |
| 저장/공유 | Web Share API 활용 |
| 캘린더 | 날짜별 로그 조회 UI |
| 설정 | 방 나가기, 퀘스트 관리 진입 |
| 로컬 세션 | device_id, room_id, participant_id localStorage 저장 |

**Android 기능**

| 기능 | 설명 |
| --- | --- |
| WebView 앱 | 서버의 웹 SPA를 Android 앱 안에서 실행 |
| 서버 주소 설정 | ngrok URL 등 외부 서버 주소 저장 |
| SharedPreferences | 서버 URL 저장 |
| 카메라/마이크 권한 | WebView 내 촬영을 위한 권한 요청 |
| 파일 선택 처리 | WebChromeClient 파일 chooser 지원 |
| 딥링크 | `snapchal://join/{code}` 형태 초대 링크 처리 |
| 새로고침/설정 메뉴 | 앱 메뉴에서 reload, server settings 제공 |
| Cleartext 허용 | HTTP 서버 접속 가능하도록 설정 |

**API 목록**

| Method | Endpoint | 기능 |
| --- | --- | --- |
| POST | `/api/rooms` | 방 생성 |
| GET | `/api/rooms/code/{join_code}` | 참여 코드로 방 조회 |
| POST | `/api/rooms/{room_id}/join` | 방 참여 |
| GET | `/api/rooms/{room_id}` | 방 상세 조회 |
| POST | `/api/rooms/{room_id}/leave` | 방 나가기 |
| GET | `/api/rooms/{room_id}/quest-candidates` | 퀘스트 후보 3개 조회 |
| GET | `/api/rooms/{room_id}/today` | 오늘 퀘스트 상태 조회 |
| POST | `/api/rooms/{room_id}/quest` | 오늘 퀘스트 선택 |
| GET | `/api/rooms/{room_id}/mission/{hour_slot}` | 시간대 미션 조회 |
| GET | `/api/rooms/{room_id}/logs/{log_date}` | 날짜별 로그 조회 |
| POST | `/api/videos/upload` | 영상 업로드 |
| GET | `/api/videos/{video_id}/stream` | 영상 스트리밍 |
| DELETE | `/api/videos/{video_id}` | 영상 삭제/숨김 |
| POST | `/api/reactions` | 이모지 반응 추가 |
| POST | `/api/rooms/{room_id}/share` | 저장/공유 기록 |
| GET | `/api/admin/quests` | 퀘스트 목록 관리 |
| PATCH | `/api/admin/quests/{template_id}` | 퀘스트 수정 |

**퀘스트 콘텐츠**

| 모드 | 개수 | 퀘스트 |
| --- | --- | --- |
| 친구 모드 | 6개 | 무지개 로그, 같은 포즈 챌린지, 내 주변 가장 웃긴 거, 공통 주제 로그, 우리는 하나 컨셉, 금지 장면 게임 |
| 커플 모드 | 6개 | 같은 하루 다른 시선, 서로에게 보내는 순간, 취향 교환 로그, 만나는 날 로그, 서로 따라하기, 오늘의 마음 날씨 |
| 시간대 | 18개/퀘스트 | `06:00`부터 `23:00`까지 시간별 미션 |

**현재 MVP 성격**

| 항목 | 상태 |
| --- | --- |
| 인증 | 별도 로그인 없음, device_id 기반 |
| 저장소 | 로컬 SQLite + 로컬 uploads 폴더 |
| 실시간성 | WebSocket 없음, 조회/새로고침 기반 |
| 영상 포맷 | WebM 중심 |
| 배포 | 로컬 서버 + ngrok 시연 흐름 |
| 앱 구조 | 네이티브 앱이라기보다 WebView 래퍼 + 웹 SPA |

---

**퀘스트 기획 정리**

| 구분 | 기획 방향 | 현재 MVP 반영 | 확장 가능성 |
| --- | --- | --- | --- |
| 퀘스트의 역할 | 사용자가 “무엇을 찍을지” 고민하지 않게 만들고, 하루 로그 전체를 하나의 컨셉으로 묶는 장치 | 하루 첫 접근자가 후보 3개 중 1개 선택 | 개인/관계/시즌/날씨/기념일 기반 추천으로 확장 |
| 운영 단위 | 단발 미션이 아니라 하루 단위 로그 주제 | 선택된 퀘스트는 당일 변경 불가 | 연속 참여, 주간 챌린지, 이벤트형 퀘스트 운영 가능 |
| 모드 구분 | 친구/커플 관계에 맞는 다른 촬영 이유 제공 | 친구 모드 6개, 커플 모드 6개 | 가족, 팀, 동아리, 여행, 생일 등 관계별 팩 확장 |
| 시간대 미션 | 같은 주제를 시간대별로 작게 쪼개 촬영 부담을 낮춤 | 06:00~23:00, 퀘스트당 18개 미션 | 사용자 생활 패턴에 맞춘 시간대 재구성, 놓친 시간 보정 |
| 퀘스트 생성 | MVP에서는 안정성을 위해 사전 생성 데이터 사용 | FastAPI startup 시 seed 데이터 적재 | LLM 기반 자동 생성, 운영자 큐레이션, 사용자 제안 퀘스트 |
| 성과 지표 | 퀘스트가 촬영 이유와 공유 욕구를 만드는지 검증 | 후보 노출, 선택, 미션 조회, 업로드, 저장/공유 이벤트 기록 | 퀘스트별 완주율, 재선택률, 공유율, 관계 유형별 반응 분석 |

**추후 구현 방향**

| 우선순위 | 기능 | 구현 방향 | 목적 |
| --- | --- | --- | --- |
| Phase 1 | 영상 스티커 꾸미기 | 녹화 후 미리보기 화면에서 스티커, 텍스트, 날짜, 퀘스트명, 참여자 이름을 오버레이 | 저장/공유 결과물을 더 예쁘게 만들고 SNS 공유율 증가 |
| Phase 1 | 퀘스트 워터마크 | 공유용 결과물에 `SnapChal`, 퀘스트명, 날짜를 자동 삽입 | 브랜드 노출과 재유입 유도 |
| Phase 1 | 공유 결과물 고도화 | 시간대별 클립을 세로형/가로형 템플릿으로 합성하고 저장 품질 개선 | 단순 로그 조회를 넘어 공유 가능한 완성물 제공 |
| Phase 2 | 프리미엄 스티커/이펙트 | 스티커 사진 감성의 프레임, 낙서, 필터, 시즌 장식을 유료/광고 보상형으로 제공 | 꾸미기 기능을 직접 수익화 포인트로 연결 |
| Phase 2 | 알림/리마인드 | 시간대 미션 알림, 친구 미참여 알림, 하루 마감 알림 추가 | 촬영 누락 감소와 완주율 개선 |
| Phase 2 | 과거 로그 안정화 | 날짜별 로그 보관, 삭제 정책, 저장소 분리, 클립 메타데이터 정리 | 반복 사용 가능한 기록 서비스로 전환 |
| Phase 3 | LLM 퀘스트 생성 | 모드, 관계, 기념일, 날씨, 최근 참여 패턴을 입력으로 맞춤 퀘스트 생성 | 콘텐츠 반복감을 줄이고 개인화 강화 |
| Phase 3 | 성장형 수집 요소 | 출석, 공유, 퀘스트 완주율에 따라 방 단위 수집/성장 요소 제공 | 장기 리텐션과 방 유지율 개선 |
| Phase 3 | 브랜드/이벤트 퀘스트 | 시즌, 장소, 브랜드 캠페인에 맞춘 스폰서 퀘스트 운영 | B2B성 수익 모델과 바이럴 캠페인 연결 |

**BM 구조**

| 단계 | 수익 모델 | 내용 | 핵심 논리 |
| --- | --- | --- | --- |
| 1 | 무료 핵심 기능 | 방 생성, 초대, 퀘스트 선택, 2초 촬영, 로그 보기, 기본 공유는 무료 제공 | 초기에는 사용성과 관계 기반 확산을 우선 검증 |
| 2 | Rewarded Ad | 광고 1회 시청 시 특별 스티커, 프레임, 공유 템플릿을 일회성 사용 | 무료 사용자를 유지하면서 꾸미기 욕구를 수익화 |
| 3 | 프리미엄 구독 | 광고 제거, 스티커/이펙트 무제한, 고화질 저장, 프리미엄 공유 템플릿 제공 | 셋로그식 구독 구조와 스노우식 꾸미기 수익화를 결합 |
| 4 | 인앱 구매 | 크리스마스, 여름 여행, 커플 기념일, 시험기간 등 시즌 퀘스트 팩 판매 | 퀘스트 자체를 콘텐츠 상품으로 확장 |
| 5 | 브랜드 스폰서 퀘스트 | 브랜드 캠페인형 미션, 장소 기반 챌린지, 한정 스티커/프레임 연동 | 사용자의 공유 결과물이 자연스러운 캠페인 매체가 됨 |

**수익화 로드맵**

| Phase | 시점 | 집중할 것 | 검증 지표 |
| --- | --- | --- | --- |
| Phase 0 | MVP | 퀘스트가 촬영 이유를 만드는지 검증 | 퀘스트 선택률, 시간대별 촬영률, 저장/공유율 |
| Phase 1 | MVP 안정화 후 | 스티커 꾸미기, 워터마크, 공유 템플릿 | 꾸미기 사용률, 공유 전환율, 저장 전환율 |
| Phase 2 | 초기 사용자 확보 후 | Rewarded Ad, 프리미엄 구독 | 광고 시청률, 구독 전환율, 유료 기능 재사용률 |
| Phase 3 | 콘텐츠 반복 사용 확인 후 | 시즌 퀘스트 팩, 브랜드 스폰서 퀘스트 | 퀘스트 팩 구매율, 캠페인 참여율, 공유 도달 |

**정리**

스냅챌의 핵심 차별점은 “2초 영상” 자체보다 **퀘스트가 매일 찍을 이유를 만든다**는 점이다. MVP는 이 가설을 검증하는 단계이고, 이후 수익화는 영상 꾸미기와 공유 결과물의 품질을 높이는 방향에서 시작하는 것이 자연스럽다. 장기적으로는 퀘스트를 단순 기능이 아니라 시즌 팩, 관계별 팩, 브랜드 캠페인까지 확장 가능한 콘텐츠 단위로 보는 구조가 적합하다.