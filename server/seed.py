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
# 견종 다양성을 보여주는 큐레이션 더미들(시연용). breed가 픽셀 외형을 결정하고,
# 일부는 appearance.equipped로 옷을 입혀 꾸미기 기능을 미리 보여준다.
DEMO_DUMMIES = [
    {"token": DEMO_DUMMY_PREFIX + "choco", "nickname": "한강 초코", "pet_name": "초코", "breed": "푸들",
     "size": "small", "tags": ["온순함", "낯가림 없음"], "sociality": 4, "activity_level": 3,
     "walk_style": "sniff", "lat": 37.5006, "lng": 127.0406, "appearance": {"equipped": ["bandana"]}},
    {"token": DEMO_DUMMY_PREFIX + "kong", "nickname": "테헤란 콩", "pet_name": "콩", "breed": "말티즈",
     "size": "small", "tags": ["활발함", "공놀이 좋아함"], "sociality": 5, "activity_level": 4,
     "walk_style": "active", "lat": 37.5014, "lng": 127.0402},
    {"token": DEMO_DUMMY_PREFIX + "mochi", "nickname": "역삼 모찌", "pet_name": "모찌", "breed": "시바견",
     "size": "medium", "tags": ["호기심", "마이웨이"], "sociality": 3, "activity_level": 4,
     "walk_style": "normal", "lat": 37.5012, "lng": 127.0411, "appearance": {"equipped": ["bowtie"]}},
    {"token": DEMO_DUMMY_PREFIX + "bori", "nickname": "선릉 보리", "pet_name": "보리", "breed": "웰시코기",
     "size": "medium", "tags": ["활발함", "먹보"], "sociality": 5, "activity_level": 5,
     "walk_style": "active", "lat": 37.5001, "lng": 127.0392},
    {"token": DEMO_DUMMY_PREFIX + "happy", "nickname": "테헤란 해피", "pet_name": "해피", "breed": "골든리트리버",
     "size": "large", "tags": ["온순함", "사람 좋아함"], "sociality": 5, "activity_level": 3,
     "walk_style": "sniff", "lat": 37.5018, "lng": 127.0399, "appearance": {"equipped": ["scarf"]}},
    {"token": DEMO_DUMMY_PREFIX + "latte", "nickname": "강남 라떼", "pet_name": "라떼", "breed": "닥스훈트",
     "size": "small", "tags": ["겁많음", "낯가림"], "sociality": 2, "activity_level": 3,
     "walk_style": "slow", "lat": 37.4999, "lng": 127.0405},
    {"token": DEMO_DUMMY_PREFIX + "cloud", "nickname": "포스코 구름", "pet_name": "구름", "breed": "비숑",
     "size": "small", "tags": ["활발함", "장난꾸러기"], "sociality": 4, "activity_level": 4,
     "walk_style": "active", "lat": 37.5009, "lng": 127.0414, "appearance": {"equipped": ["cap"]}},
]

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
    db.commit()


def run() -> None:
    db = SessionLocal()
    try:
        _load(db)
        _ensure_demo_dummies(db)
    finally:
        db.close()
