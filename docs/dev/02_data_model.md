# DB 스키마 및 데이터 모델

> Phase 1 웹 MVP 기준. Supabase PostgreSQL + PostGIS 사용.
> Phase 3 이후 확장 항목은 별도 표기.

---

## 테이블 목록

| 테이블명 | 설명 |
|---|---|
| `users` | 보호자 계정 정보 |
| `pets` | 반려견 프로필 |
| `walk_sessions` | 개인 산책 세션 (산책 시작~종료) |
| `match_requests` | 같이 산책하기 요청 |
| `match_sessions` | 매칭 세션 (두 사용자 공동 산책) |
| `match_logs` | 매칭 완료 후 기록 |
| `friendships` | 친구 관계 |
| `blocks` | 차단 목록 |
| `reports` | 신고 내역 |
| `intimacy_scores` | 친밀도 점수 (Phase 2~3) |

---

## users

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `id` | uuid PK | 사용자 ID |
| `email` | text UNIQUE | 이메일 |
| `nickname` | text | 닉네임 |
| `profile_image_url` | text | 프로필 이미지 |
| `created_at` | timestamptz | 가입일 |
| `updated_at` | timestamptz | 수정일 |

---

## pets

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `id` | uuid PK | 반려견 ID |
| `user_id` | uuid FK → users | 보호자 |
| `name` | text | 이름 |
| `photo_url` | text | 사진 |
| `breed` | text | 견종 |
| `age_months` | int | 나이 (개월 수) |
| `gender` | text | `male` / `female` |
| `size` | text | `small` / `medium` / `large` |
| `is_neutered` | boolean | 중성화 여부 |
| `personality_tags` | text[] | 성격 태그 배열 |
| `sociality` | int | 사회성 점수 (1~5) |
| `activity_level` | int | 활동량 (1~5) |
| `walk_style` | text | `slow` / `normal` / `fast` |
| `preferred_partner_size` | text[] | 선호 친구 크기 |
| `caution_notes` | text | 주의사항 |
| `created_at` | timestamptz | |

---

## walk_sessions

> 한 사용자의 산책 세션. 산책 시작 시 생성, 종료 시 closed.

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `id` | uuid PK | 세션 ID |
| `user_id` | uuid FK → users | 산책 중인 사용자 |
| `pet_id` | uuid FK → pets | 함께 산책 중인 반려견 |
| `status` | text | `active` / `closed` |
| `started_at` | timestamptz | 산책 시작 시간 |
| `ended_at` | timestamptz | 산책 종료 시간 |
| `last_location` | geography(Point, 4326) | 마지막 위치 (PostGIS) |
| `location_updated_at` | timestamptz | 위치 마지막 업데이트 시간 |
| `is_location_visible` | boolean | 지도 노출 여부 |

> `last_location`에 PostGIS 공간 인덱스(`GIST`) 적용 필요

---

## match_requests

> 같이 산책하기 요청.

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `id` | uuid PK | 요청 ID |
| `requester_id` | uuid FK → users | 요청 보낸 사용자 |
| `receiver_id` | uuid FK → users | 요청 받은 사용자 |
| `requester_walk_session_id` | uuid FK → walk_sessions | |
| `receiver_walk_session_id` | uuid FK → walk_sessions | |
| `status` | text | `pending` / `accepted` / `rejected` / `expired` / `cancelled` |
| `expires_at` | timestamptz | 요청 만료 시간 |
| `created_at` | timestamptz | |
| `updated_at` | timestamptz | |

---

## match_sessions

> 요청 수락 후 생성되는 공동 산책 세션.

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `id` | uuid PK | 매칭 세션 ID |
| `match_request_id` | uuid FK → match_requests | |
| `user_a_id` | uuid FK → users | |
| `user_b_id` | uuid FK → users | |
| `pet_a_id` | uuid FK → pets | |
| `pet_b_id` | uuid FK → pets | |
| `status` | text | `active` / `ended` / `cancelled` |
| `started_at` | timestamptz | |
| `ended_at` | timestamptz | |

---

## match_logs

> 매칭 종료 후 생성되는 기록.

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `id` | uuid PK | 로그 ID |
| `match_session_id` | uuid FK → match_sessions | |
| `user_a_id` | uuid FK → users | |
| `user_b_id` | uuid FK → users | |
| `pet_a_id` | uuid FK → pets | |
| `pet_b_id` | uuid FK → pets | |
| `walked_at` | date | 산책 날짜 |
| `duration_minutes` | int | 동행 시간 (분) |
| `distance_meters` | int | 이동 거리 (선택) |
| `photo_urls` | text[] | 사진 (선택) |
| `feedback_a` | text | user_a의 피드백 (`positive` / `neutral` / `negative`) |
| `feedback_b` | text | user_b의 피드백 |
| `created_at` | timestamptz | |

> 피드백은 상대방에게 공개하지 않는다.

---

## friendships

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `id` | uuid PK | |
| `requester_id` | uuid FK → users | 친구 요청 보낸 사용자 |
| `receiver_id` | uuid FK → users | 친구 요청 받은 사용자 |
| `status` | text | `pending` / `accepted` / `rejected` |
| `created_at` | timestamptz | |
| `updated_at` | timestamptz | |

> 친구 요청은 match_logs가 1건 이상 존재하는 상대에게만 가능.

---

## blocks

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `id` | uuid PK | |
| `blocker_id` | uuid FK → users | 차단한 사용자 |
| `blocked_id` | uuid FK → users | 차단된 사용자 |
| `created_at` | timestamptz | |

---

## reports

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `id` | uuid PK | |
| `reporter_id` | uuid FK → users | 신고한 사용자 |
| `reported_id` | uuid FK → users | 신고된 사용자 |
| `reason` | text | 신고 사유 |
| `context` | text | 상세 내용 (선택) |
| `created_at` | timestamptz | |

---

## intimacy_scores (Phase 2~3)

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `id` | uuid PK | |
| `pet_a_id` | uuid FK → pets | |
| `pet_b_id` | uuid FK → pets | |
| `score` | int | 친밀도 점수 |
| `meet_count` | int | 총 만남 횟수 |
| `last_met_at` | timestamptz | 마지막 만남 |
| `updated_at` | timestamptz | |

---

## ERD 관계 요약

```
users ──< pets
users ──< walk_sessions >── pets
users ──< match_requests >── users
match_requests ──< match_sessions
match_sessions ──< match_logs
users ──< friendships >── users
users ──< blocks >── users
pets ──< intimacy_scores >── pets
```
