# 퀘스트 Seed 데이터 명세 (F-12)

> 서버 startup 시 `seed.py`가 `quest_templates` + `quest_missions`를 적재한다(이미 있으면 skip).
> 기획 근거·운영 방식은 [mvp_planning/01_feature_spec.md F-12](../mvp_planning/01_feature_spec.md) 참조.

---

## 구조

```
quest_template (mode, title, description)
   └─ quest_mission[] (order, title, hint)   # "산책 중 찍어볼 순간"들
```

- `mode`: `solo`(혼자 산책) / `match`(매칭 산책) / `walk_friend`(방-산책친구) / `family`(방-가족)
- 퀘스트당 미션 3~5개 권장(과하면 부담 → 촬영 부담 완화 원칙 위배).
- 모드별 최소 4~6개 퀘스트 → `GET /quests/candidates`가 랜덤 3개 추천.

---

## Seed 형식 (예: Python dict)

```python
QUESTS = [
  {
    "mode": "solo",
    "title": "오늘의 날씨 산책",
    "description": "오늘 하늘과 날씨를 우리 강아지와 함께 담아보세요.",
    "missions": [
      {"order": 1, "title": "산책 출발 순간", "hint": "현관/엘리베이터 앞 설렘"},
      {"order": 2, "title": "오늘의 하늘 한 컷", "hint": "강아지와 하늘이 같이"},
      {"order": 3, "title": "가장 신난 순간", "hint": "뛰거나 냄새 맡을 때"},
    ],
  },
  # ...
]
```

---

## 샘플 콘텐츠 (모드별)

### solo (혼자 산책)
| 퀘스트 | 미션 예시 |
|---|---|
| 오늘의 날씨 산책 | 출발 순간 · 오늘의 하늘 · 가장 신난 순간 |
| 우리 동네 한 컷 | 단골 코스 · 처음 보는 골목 · 동네 랜드마크 |
| 강아지 표정 모음 | 출발 표정 · 집중 표정 · 만족 표정 |
| 새로 간 길 | 갈림길 선택 · 새 풍경 · 돌아오는 길 |

### match (매칭 산책)
| 퀘스트 | 미션 예시 |
|---|---|
| 같이 만난 친구 | 첫 인사 · 나란히 걷기 · 헤어지는 순간 |
| 둘의 산책 속도 | 누가 더 빠른가 · 쉬는 타이밍 · 보폭 맞추기 |
| 오늘의 베프 | 친구 클로즈업 · 둘이 한 프레임 · 베스트 컷 |

### walk_friend (방 — 산책 친구)
| 퀘스트 | 미션 예시 |
|---|---|
| 같은 주제 다른 시선 | 각자의 출발 · 각자의 하이라이트 · 각자의 마무리 |
| 오늘의 베스트 컷 | 내 강아지 자랑 · 웃긴 순간 · 멋진 순간 |

### family (방 — 가족)
| 퀘스트 | 미션 예시 |
|---|---|
| 우리 가족 산책 | 누가 산책시키나 · 함께 걷기 · 집 도착 |
| 하루의 기록 | 아침 산책 · 저녁 산책 · 잠들기 전 |

---

## 적재 규칙 (`seed.py`)
1. startup 시 `quest_templates` 비어있으면 `QUESTS` 적재.
2. 각 template insert 후 missions를 `order`대로 insert.
3. `is_active=True` 기본. 운영자는 `PATCH /api/admin/quests/{id}`로 토글/수정.
4. 멱등: 재기동 시 중복 적재 금지(존재 여부 확인).

---

## 확장 (MVP 이후, 구현 범위 밖)
- LLM 기반 맞춤 퀘스트 생성(관계·날씨·기념일·최근 패턴)
- 시즌/이벤트 퀘스트, 관계별 팩 확장
> 수익화형 스폰서 퀘스트는 기획 결정에 따라 본 MVP에서 다루지 않는다.
