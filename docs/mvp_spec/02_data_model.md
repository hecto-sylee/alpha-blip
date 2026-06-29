# 데이터 모델 (SQLite / SQLAlchemy)

> [dev/02_data_model.md](../dev/02_data_model.md)의 PostgreSQL 스키마를 **SQLite 구현 기준**으로 옮기고,
> snapchal 융합으로 추가된 **방·퀘스트·2초 클립·반응·기록**을 포함한다.
> PostGIS `geography` → SQLite는 `lat`/`lng` FLOAT 컬럼 + 앱 레벨 거리 계산으로 대체.

---

## 테이블 목록

| 테이블 | 시스템 | 설명 |
|---|---|---|
| `users` | 공통 | 보호자 계정 (MVP: 게스트) |
| `pets` | 공통(F-02) | 반려견 프로필 |
| `walk_sessions` | S1(F-01) | 개인 산책 세션 |
| `match_requests` | S1(F-03) | 같이 산책하기 요청 |
| `match_sessions` | S1(F-04) | 공동 산책 세션 |
| `match_logs` | S1(F-05) | 매칭 로그 |
| `records` | S3(F-10) | 산책 기록(다이어리 엔트리) |
| `clips` | S3(F-10) | 2초 영상 클립 |
| `rooms` | S3(F-11) | 방 |
| `room_members` | S3(F-11) | 방 참여자 |
| `reactions` | S3(F-11) | 이모지 반응 |
| `quest_templates` | S3(F-12) | 퀘스트 템플릿(seed) |
| `quest_missions` | S3(F-12) | 퀘스트별 산책 미션(seed) |
| `daily_quests` | S3(F-12) | 특정 날짜에 선택된 퀘스트(user/room) |
| `blocks` | F-09 | 차단 |
| `reports` | F-09 | 신고 |
| `analytics_events` | 공통 | 행동 이벤트 로그 |

> ID는 전부 `String` UUID(hex) PK. 시간은 `DateTime`(UTC). 불리언/enum은 `String`/`Boolean`.

---

## 공통 / S1 (dev/02 기준 — SQLite 적응)

### users
| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | str PK | |
| nickname | str | 닉네임 (MVP 필수 입력) |
| email | str null | 후순위 |
| profile_image_url | str null | |
| auth_token | str | 게스트 세션 토큰 (localStorage 저장) |
| created_at | datetime | |

### pets
`dev/02_data_model.md`의 `pets`와 동일. SQLite에서 `personality_tags`/`preferred_partner_size`는 **JSON 문자열**(`Text`)로 저장.

### walk_sessions
| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | str PK | |
| user_id | str FK→users | |
| pet_id | str FK→pets | |
| status | str | `active`/`closed` |
| lat / lng | float null | 마지막 위치 (PostGIS 대체) |
| location_updated_at | datetime null | |
| is_location_visible | bool | 지도 노출 여부 (기본 true) |
| started_at / ended_at | datetime | |

> 근처 검색은 `status='active' AND is_location_visible` 인 세션을 **앱 레벨 Haversine**로 필터. (`utils/geo.py`)

### match_requests / match_sessions / match_logs
`dev/02_data_model.md`와 동일 컬럼. enum 값 그대로(`pending/accepted/rejected/expired/cancelled` 등). `match_logs.photo_urls`는 JSON 문자열.

---

## S3 — 기록 / 클립 (F-10)

### records
하나의 산책 = 하나의 기록 엔트리.

| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | str PK | |
| user_id | str FK→users | 작성자 |
| walk_session_id | str FK null | 혼자 산책 출처 |
| match_session_id | str FK null | 매칭 산책 출처 |
| daily_quest_id | str FK→daily_quests null | 연결된 오늘의 퀘스트 |
| visibility | str | `diary`(일기) / `room` |
| room_id | str FK→rooms null | `visibility=room`일 때 |
| walked_at | date | 산책 날짜 (캘린더 키) |
| duration_minutes | int null | |
| distance_meters | int null | |
| text | text null | 본문 |
| decoration_json | text null | 스티커/그림 등 꾸미기 데이터(JSON) |
| created_at | datetime | |

### clips
2초 영상 클립. 한 record에 여러 clip.

| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | str PK | |
| record_id | str FK→records | |
| user_id | str FK→users | |
| mission_id | str FK→quest_missions null | 어떤 미션의 클립인지 |
| file_path | str | `uploads/{id}.webm` |
| duration_ms | int | ≈2000 (클라이언트 강제) |
| order | int | 기록 내 정렬 |
| status | str | `active`/`hidden` |
| created_at | datetime | |

> 삭제는 물리 삭제 대신 `status='hidden'` (본인 당일 클립만). 스트리밍은 `GET /api/clips/{id}/stream`.

---

## S3 — 방 / 반응 (F-11)

### rooms
| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | str PK | |
| name | str | 방 이름 |
| mode | str | `walk_friend`/`family` (퀘스트 팩 결정) |
| join_code | str unique | 6자리 |
| owner_id | str FK→users | 생성자(방장) |
| max_members | int | 기본 5 (TBD) |
| status | str | `active`/`deleted` |
| created_at | datetime | |

### room_members
| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | str PK | |
| room_id | str FK→rooms | |
| user_id | str FK→users | |
| status | str | `joined`/`left` |
| joined_at | datetime | |

> 제약: `(room_id, user_id)` 유니크 → 중복 참여 방지(기존 멤버 반환). 모든 멤버 `left` → room `deleted`.

### reactions
| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | str PK | |
| target_type | str | `record`/`clip` |
| target_id | str | 대상 ID |
| user_id | str FK→users | |
| emoji | str | ❤️ 😂 🔥 👍 😮 중 1 |
| created_at | datetime | |

> 제약: `(target_type, target_id, user_id, emoji)` 유니크 → 중복 토글.

---

## S3 — 퀘스트 (F-12)

### quest_templates (seed)
| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | str PK | |
| mode | str | `solo`/`match`/`walk_friend`/`family` |
| title | str | 퀘스트명 |
| description | str | 설명 |
| is_active | bool | 관리 토글 |

### quest_missions (seed)
| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | str PK | |
| quest_template_id | str FK→quest_templates | |
| order | int | 미션 순서 |
| title | str | "지금 찍어볼 순간" |
| hint | str null | 촬영 가이드 |

> 시간대(06–23시) 슬롯 대신 **산책 중 순간 미션** 리스트로 구성. (06_quest_seed.md)

### daily_quests
"오늘의 퀘스트" — 특정 날짜, 특정 주체(개인/방)가 선택한 1개.

| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | str PK | |
| scope | str | `user`/`room` |
| scope_id | str | user_id 또는 room_id |
| quest_template_id | str FK→quest_templates | |
| quest_date | date | 해당 날짜 |
| locked | bool | 선택 후 true (당일 변경 불가) |
| created_at | datetime | |

> 제약: `(scope, scope_id, quest_date)` 유니크 → 하루 1개. 방은 첫 시작 멤버가 생성하면 공유.

---

## F-09 / 공통

### blocks / reports
`dev/02_data_model.md`와 동일.

### analytics_events
| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | str PK | |
| user_id | str FK null | |
| type | str | `room_create`/`room_join`/`quest_select`/`clip_upload`/`reaction`/`match_request`/`record_save` 등 |
| payload_json | text null | 부가 데이터 |
| created_at | datetime | |

> 모든 핵심 행동에서 1줄 적재 → [00_implementation_plan 지표](./00_implementation_plan.md) 검증.

---

## 관계 요약

```
users ──< pets
users ──< walk_sessions >── pets
users ──< match_requests >── users → match_sessions → match_logs
users ──< records >── daily_quests >── quest_templates ──< quest_missions
records ──< clips >── quest_missions
rooms ──< room_members >── users
rooms ──< records (visibility=room)
records/clips ──< reactions >── users
daily_quests(scope=user|room) ── users / rooms
```
