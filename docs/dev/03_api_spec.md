# API 명세

> Phase 1 웹 MVP 기준. Supabase 사용 시 일부는 Supabase Client SDK로 대체 가능.
> Base URL: `/api/v1`

---

## 목차

| 도메인 | 설명 |
|---|---|
| [Auth](#auth) | 인증 |
| [Users](#users) | 사용자 |
| [Pets](#pets) | 반려견 프로필 |
| [Walks](#walks) | 산책 세션 |
| [Nearby](#nearby) | 근처 산책 중인 강아지 조회 |
| [Match Requests](#match-requests) | 같이 산책하기 요청 |
| [Match Sessions](#match-sessions) | 매칭 세션 |
| [Match Logs](#match-logs) | 매칭 로그 |
| [Friends](#friends) | 친구 시스템 |
| [Privacy](#privacy) | 개인정보 보호 설정 |

---

## Auth

### POST /auth/signup
회원가입

**Request Body**
```json
{
  "email": "string",
  "password": "string",
  "nickname": "string"
}
```

**Response** `201`
```json
{
  "user_id": "uuid",
  "access_token": "string"
}
```

---

### POST /auth/login
로그인

**Request Body**
```json
{
  "email": "string",
  "password": "string"
}
```

**Response** `200`
```json
{
  "user_id": "uuid",
  "access_token": "string"
}
```

---

## Users

### GET /users/me
내 프로필 조회

**Response** `200`
```json
{
  "id": "uuid",
  "nickname": "string",
  "profile_image_url": "string"
}
```

---

### PATCH /users/me
내 프로필 수정

**Request Body** (변경 항목만 포함)
```json
{
  "nickname": "string",
  "profile_image_url": "string"
}
```

---

## Pets

### POST /pets
반려견 등록

**Request Body**
```json
{
  "name": "string",
  "photo_url": "string",
  "breed": "string",
  "age_months": 24,
  "gender": "male | female",
  "size": "small | medium | large",
  "is_neutered": true,
  "personality_tags": ["활발함", "강아지 좋아함"],
  "sociality": 4,
  "activity_level": 3,
  "walk_style": "normal",
  "preferred_partner_size": ["small", "medium"],
  "caution_notes": "string"
}
```

**Response** `201`
```json
{
  "pet_id": "uuid"
}
```

---

### GET /pets/:pet_id
반려견 프로필 조회

**Response** `200`
```json
{
  "id": "uuid",
  "name": "string",
  "photo_url": "string",
  "breed": "string",
  "age_months": 24,
  "gender": "male",
  "size": "small",
  "is_neutered": true,
  "personality_tags": ["활발함"],
  "sociality": 4,
  "activity_level": 3,
  "walk_style": "normal",
  "caution_notes": "string"
}
```

---

### PATCH /pets/:pet_id
반려견 프로필 수정 (본인 소유만 가능)

---

## Walks

### POST /walks/start
산책 시작

**Request Body**
```json
{
  "pet_id": "uuid",
  "latitude": 37.5665,
  "longitude": 126.9780
}
```

**Response** `201`
```json
{
  "walk_session_id": "uuid",
  "started_at": "ISO8601"
}
```

---

### PATCH /walks/:session_id/location
위치 업데이트 (산책 중 주기적 호출)

**Request Body**
```json
{
  "latitude": 37.5665,
  "longitude": 126.9780
}
```

**Response** `200`

---

### POST /walks/:session_id/end
산책 종료

**Response** `200`
```json
{
  "ended_at": "ISO8601",
  "duration_minutes": 30
}
```

---

## Nearby

### GET /nearby/dogs
근처 산책 중인 강아지 목록 조회

**Query Parameters**
| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `latitude` | float | ✅ | 현재 위도 |
| `longitude` | float | ✅ | 현재 경도 |
| `radius_meters` | int | ❌ | 검색 반경 (기본값: 500) |
| `size` | string | ❌ | 필터: `small` / `medium` / `large` |

**Response** `200`
```json
{
  "dogs": [
    {
      "walk_session_id": "uuid",
      "pet": {
        "id": "uuid",
        "name": "string",
        "breed": "string",
        "size": "small",
        "personality_tags": ["활발함"]
      },
      "distance_meters": 230,
      "approximate_location": {
        "latitude": 37.567,
        "longitude": 126.978
      }
    }
  ]
}
```

> `approximate_location`은 실제 위치에서 무작위 오프셋을 적용한 대략적 위치

---

## Match Requests

### POST /match-requests
같이 산책하기 요청 전송

**Request Body**
```json
{
  "receiver_walk_session_id": "uuid"
}
```

**Response** `201`
```json
{
  "match_request_id": "uuid",
  "expires_at": "ISO8601"
}
```

---

### PATCH /match-requests/:request_id/accept
요청 수락

**Response** `200`
```json
{
  "match_session_id": "uuid"
}
```

---

### PATCH /match-requests/:request_id/reject
요청 거절

**Response** `200`

---

### DELETE /match-requests/:request_id
요청 취소 (요청자만 가능)

**Response** `200`

---

### GET /match-requests/incoming
받은 요청 목록

**Response** `200`
```json
{
  "requests": [
    {
      "id": "uuid",
      "requester": { "nickname": "string" },
      "pet": { "name": "string", "breed": "string" },
      "status": "pending",
      "expires_at": "ISO8601",
      "created_at": "ISO8601"
    }
  ]
}
```

---

## Match Sessions

### GET /match-sessions/:session_id
매칭 세션 정보 조회

**Response** `200`
```json
{
  "id": "uuid",
  "status": "active",
  "partner": {
    "nickname": "string",
    "pet": { "name": "string", "breed": "string" }
  },
  "started_at": "ISO8601"
}
```

---

### POST /match-sessions/:session_id/end
산책 종료 (두 사용자 중 한 명이 종료 가능)

**Response** `200`
```json
{
  "match_log_id": "uuid"
}
```

---

### POST /match-sessions/:session_id/cancel
매칭 취소 (세션 중 이탈)

---

## Match Logs

### GET /match-logs
내 매칭 로그 목록

**Response** `200`
```json
{
  "logs": [
    {
      "id": "uuid",
      "partner_pet": { "name": "string", "breed": "string", "photo_url": "string" },
      "walked_at": "2026-06-05",
      "duration_minutes": 35,
      "meet_count": 3
    }
  ]
}
```

---

### PATCH /match-logs/:log_id/feedback
산책 후 피드백 제출

**Request Body**
```json
{
  "feedback": "positive | neutral | negative"
}
```

> 피드백은 상대방에게 노출되지 않는다.

---

## Friends

### POST /friends/request
친구 요청 (match_log 1건 이상인 상대만 가능)

**Request Body**
```json
{
  "receiver_id": "uuid"
}
```

---

### PATCH /friends/:request_id/accept
친구 요청 수락

---

### PATCH /friends/:request_id/reject
친구 요청 거절

---

### GET /friends
친구 목록

**Response** `200`
```json
{
  "friends": [
    {
      "user_id": "uuid",
      "nickname": "string",
      "pet": { "name": "string", "photo_url": "string" },
      "last_walked_at": "2026-06-01",
      "meet_count": 5
    }
  ]
}
```

---

### DELETE /friends/:user_id
친구 삭제

---

## Privacy

### POST /privacy/block
사용자 차단

**Request Body**
```json
{
  "target_user_id": "uuid"
}
```

---

### DELETE /privacy/block/:user_id
차단 해제

---

### POST /privacy/report
사용자 신고

**Request Body**
```json
{
  "target_user_id": "uuid",
  "reason": "string",
  "context": "string"
}
```

---

## 공통 에러 응답

| 코드 | 의미 |
|---|---|
| `400` | 잘못된 요청 (파라미터 오류) |
| `401` | 인증 필요 |
| `403` | 권한 없음 |
| `404` | 리소스 없음 |
| `409` | 중복 요청 (예: 이미 요청 중인 상태) |
| `500` | 서버 오류 |

**에러 응답 형식**
```json
{
  "error": {
    "code": "string",
    "message": "string"
  }
}
```
