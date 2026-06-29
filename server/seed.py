"""Quest seed loader (06_quest_seed.md). Idempotent — skips if already loaded."""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import Pet, QuestMission, QuestTemplate, User, WalkSession, utcnow

# 데모 더미 친구들 — 데모 위치 근처에 고정으로 떠 있는 '매칭 대기' 유저.
# is_mock=False 라서 (1) 모든 사용자의 nearby에 보이고 (2) 매칭 요청 시 자동수락되지
# 않는다(망고만 is_mock=True 라 즉시 자동수락). 토큰으로 idempotent 하게 식별한다.
DEMO_DUMMY_PREFIX = "demo-dummy:"
# 데모 강아지 제거(사용자 요청): 더미를 더 이상 시드하지 않는다. 빈 목록이면
# _ensure_demo_dummies가 기존 더미를 지도에서 숨긴다(완전 삭제는 demo 리셋/정리 스크립트).
DEMO_DUMMIES = []

QUESTS = [
    # solo
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
    {
        "mode": "solo",
        "title": "우리 동네 한 컷",
        "description": "익숙한 동네를 새롭게 담아보세요.",
        "missions": [
            {"order": 1, "title": "단골 코스", "hint": "늘 가는 길"},
            {"order": 2, "title": "처음 보는 골목", "hint": "새 길로 한 번"},
            {"order": 3, "title": "동네 랜드마크", "hint": "우리 동네 상징"},
        ],
    },
    {
        "mode": "solo",
        "title": "강아지 표정 모음",
        "description": "산책 중 강아지의 표정을 모아보세요.",
        "missions": [
            {"order": 1, "title": "출발 표정", "hint": None},
            {"order": 2, "title": "집중 표정", "hint": "냄새 맡을 때"},
            {"order": 3, "title": "만족 표정", "hint": "돌아오는 길"},
        ],
    },
    {
        "mode": "solo",
        "title": "새로 간 길",
        "description": "오늘은 안 가본 길로.",
        "missions": [
            {"order": 1, "title": "갈림길 선택", "hint": None},
            {"order": 2, "title": "새 풍경", "hint": None},
            {"order": 3, "title": "돌아오는 길", "hint": None},
        ],
    },
    # match
    {
        "mode": "match",
        "title": "같이 만난 친구",
        "description": "오늘 만난 산책 친구와의 순간.",
        "missions": [
            {"order": 1, "title": "첫 인사", "hint": None},
            {"order": 2, "title": "나란히 걷기", "hint": None},
            {"order": 3, "title": "헤어지는 순간", "hint": None},
        ],
    },
    {
        "mode": "match",
        "title": "둘의 산책 속도",
        "description": "둘의 보폭을 맞춰보세요.",
        "missions": [
            {"order": 1, "title": "누가 더 빠른가", "hint": None},
            {"order": 2, "title": "쉬는 타이밍", "hint": None},
            {"order": 3, "title": "보폭 맞추기", "hint": None},
        ],
    },
    {
        "mode": "match",
        "title": "오늘의 베프",
        "description": "오늘의 베스트 컷.",
        "missions": [
            {"order": 1, "title": "친구 클로즈업", "hint": None},
            {"order": 2, "title": "둘이 한 프레임", "hint": None},
            {"order": 3, "title": "베스트 컷", "hint": None},
        ],
    },
    # walk_friend
    {
        "mode": "walk_friend",
        "title": "같은 주제 다른 시선",
        "description": "각자의 산책을 같은 주제로.",
        "missions": [
            {"order": 1, "title": "각자의 출발", "hint": None},
            {"order": 2, "title": "각자의 하이라이트", "hint": None},
            {"order": 3, "title": "각자의 마무리", "hint": None},
        ],
    },
    {
        "mode": "walk_friend",
        "title": "오늘의 베스트 컷",
        "description": "내 강아지를 자랑해보세요.",
        "missions": [
            {"order": 1, "title": "내 강아지 자랑", "hint": None},
            {"order": 2, "title": "웃긴 순간", "hint": None},
            {"order": 3, "title": "멋진 순간", "hint": None},
        ],
    },
    # family
    {
        "mode": "family",
        "title": "우리 가족 산책",
        "description": "가족과 함께한 산책.",
        "missions": [
            {"order": 1, "title": "누가 산책시키나", "hint": None},
            {"order": 2, "title": "함께 걷기", "hint": None},
            {"order": 3, "title": "집 도착", "hint": None},
        ],
    },
    {
        "mode": "family",
        "title": "하루의 기록",
        "description": "하루의 산책을 기록해요.",
        "missions": [
            {"order": 1, "title": "아침 산책", "hint": None},
            {"order": 2, "title": "저녁 산책", "hint": None},
            {"order": 3, "title": "잠들기 전", "hint": None},
        ],
    },
]


def _load(db: Session) -> None:
    if db.query(QuestTemplate).count() > 0:
        return
    for q in QUESTS:
        tpl = QuestTemplate(
            mode=q["mode"], title=q["title"], description=q.get("description"), is_active=True
        )
        db.add(tpl)
        db.flush()
        for m in q["missions"]:
            db.add(
                QuestMission(
                    quest_template_id=tpl.id,
                    order=m["order"],
                    title=m["title"],
                    hint=m.get("hint"),
                )
            )
    db.commit()


def _ensure_demo_dummies(db: Session) -> None:
    """초코·콩 더미 유저/펫/활성 산책을 고정 좌표로 보장한다(idempotent)."""
    for d in DEMO_DUMMIES:
        user = db.query(User).filter(User.auth_token == d["token"]).first()
        if user is None:
            user = User(nickname=d["nickname"], auth_token=d["token"], is_mock=False)
            db.add(user)
            db.flush()
        else:
            user.nickname = d["nickname"]
            user.is_mock = False  # 자동수락 대상이 아님(매칭 대기)

        appearance_json = (
            json.dumps(d["appearance"], ensure_ascii=False) if d.get("appearance") else None
        )
        pet = (
            db.query(Pet).filter(Pet.user_id == user.id).order_by(Pet.created_at.asc()).first()
        )
        if pet is None:
            pet = Pet(
                user_id=user.id,
                name=d["pet_name"],
                breed=d["breed"],
                size=d["size"],
                personality_tags=json.dumps(d["tags"], ensure_ascii=False),
                sociality=d.get("sociality"),
                activity_level=d.get("activity_level"),
                walk_style=d.get("walk_style"),
                caution_notes=d.get("caution_notes", "데모용 더미 프로필입니다."),
                appearance_json=appearance_json,
            )
            db.add(pet)
            db.flush()
        else:
            pet.name = d["pet_name"]
            pet.breed = d["breed"]
            pet.appearance_json = appearance_json

        ws = (
            db.query(WalkSession)
            .filter(WalkSession.user_id == user.id, WalkSession.status == "active")
            .order_by(WalkSession.started_at.desc())
            .first()
        )
        if ws is None:
            ws = WalkSession(user_id=user.id, pet_id=pet.id, status="active")
            db.add(ws)
            db.flush()
        ws.pet_id = pet.id
        ws.status = "active"
        ws.lat = d["lat"]
        ws.lng = d["lng"]
        ws.location_updated_at = utcnow()
        ws.is_location_visible = True

    # 목록에서 빠진 과거 더미는 지도에서 숨긴다(활성 세션 종료). 붐빔 방지 — 데이터는 보존,
    # 완전 삭제는 demo 리셋이 담당. 서버 재시작만으로 1~2마리만 남게 된다.
    keep = [d["token"] for d in DEMO_DUMMIES]
    stale = (
        db.query(User)
        .filter(User.auth_token.like(DEMO_DUMMY_PREFIX + "%"), User.auth_token.notin_(keep))
        .all()
    )
    for u in stale:
        for ws in db.query(WalkSession).filter(
            WalkSession.user_id == u.id, WalkSession.status == "active"
        ):
            ws.status = "closed"
            ws.ended_at = ws.ended_at or utcnow()
            ws.is_location_visible = False
    db.commit()


def run() -> None:
    db = SessionLocal()
    try:
        _load(db)
        _ensure_demo_dummies(db)
    finally:
        db.close()
