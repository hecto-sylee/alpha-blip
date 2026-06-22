"""Demo mode: one-device walk -> mock match -> room-share flow."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..api.pets import _to_res
from ..deps import get_current_user, get_db
from ..models import Pet, Room, RoomMember, User, WalkSession, utcnow
from ..schemas import DemoLocation, DemoSetupReq, DemoSetupRes
from ..services import room as room_svc

router = APIRouter(tags=["demo"])

DEMO_LABEL = "강남 테헤란로 큰길타워"
DEMO_LATITUDE = 37.5009
DEMO_LONGITUDE = 127.0398
DEMO_ROOM_NAME = "데모 산책방"
MOCK_NICKNAME = "테헤란로 망고"
MOCK_PET_NAME = "망고"
# 더미 사용자(망고)의 지도 위치 — 항상 이 절대좌표에 고정한다.
MOCK_LATITUDE = 37.502844
MOCK_LONGITUDE = 127.037194
MOCK_LABEL = "망고 고정 위치"


def _mock_token(user_id: str) -> str:
    return f"demo-mock:{user_id}"


def _ensure_mock_user(db: Session, owner: User) -> User:
    token = _mock_token(owner.id)
    mock = db.query(User).filter(User.auth_token == token).first()
    if mock is None:
        mock = User(
            nickname=MOCK_NICKNAME,
            email=f"demo+{owner.id}@local.invalid",
            auth_token=token,
            is_mock=True,
        )
        db.add(mock)
        db.flush()
    else:
        mock.nickname = MOCK_NICKNAME
        mock.email = mock.email or f"demo+{owner.id}@local.invalid"
        mock.is_mock = True
    return mock


def _ensure_mock_pet(db: Session, mock: User) -> Pet:
    pet = db.query(Pet).filter(Pet.user_id == mock.id).order_by(Pet.created_at.asc()).first()
    if pet is None:
        pet = Pet(
            user_id=mock.id,
            name=MOCK_PET_NAME,
            breed="비숑",
            size="small",
            personality_tags=json.dumps(["활발함", "사람 좋아함"], ensure_ascii=False),
            sociality=5,
            activity_level=4,
            walk_style="sniff",
            caution_notes="데모용 목업 프로필입니다.",
        )
        db.add(pet)
        db.flush()
    else:
        pet.name = MOCK_PET_NAME
        pet.breed = pet.breed or "비숑"
        pet.size = pet.size or "small"
        if not pet.personality_tags:
            pet.personality_tags = json.dumps(["활발함", "사람 좋아함"], ensure_ascii=False)
    return pet


def _ensure_mock_walk(db: Session, mock: User, pet: Pet) -> WalkSession:
    sessions = (
        db.query(WalkSession)
        .filter(WalkSession.user_id == mock.id, WalkSession.status == "active")
        .order_by(WalkSession.started_at.desc())
        .all()
    )
    ws = sessions[0] if sessions else None
    if ws is None:
        ws = WalkSession(user_id=mock.id, pet_id=pet.id, status="active")
        db.add(ws)
        db.flush()

    for stale in sessions[1:]:
        stale.status = "closed"
        stale.ended_at = stale.ended_at or utcnow()

    # 더미 사용자는 데모 원점과 무관하게 항상 고정 좌표에 둔다.
    ws.pet_id = pet.id
    ws.status = "active"
    ws.lat = MOCK_LATITUDE
    ws.lng = MOCK_LONGITUDE
    ws.location_updated_at = utcnow()
    ws.is_location_visible = True
    return ws


def _room_has_member(db: Session, room_id: str, user_id: str) -> bool:
    return (
        db.query(RoomMember)
        .filter(RoomMember.room_id == room_id, RoomMember.user_id == user_id, RoomMember.status == "joined")
        .first()
        is not None
    )


def _find_demo_room(db: Session, user: User, mock: User) -> Room | None:
    user_memberships = (
        db.query(RoomMember)
        .filter(RoomMember.user_id == user.id, RoomMember.status == "joined")
        .all()
    )
    for membership in user_memberships:
        room = db.get(Room, membership.room_id)
        if room is None or room.status != "active" or room.name != DEMO_ROOM_NAME:
            continue
        if _room_has_member(db, room.id, mock.id):
            return room
    return None


def _ensure_demo_room(db: Session, user: User, mock: User) -> Room:
    room = _find_demo_room(db, user, mock)
    if room is None:
        room = room_svc.create_room(db, user.id, DEMO_ROOM_NAME, "walk_friend")
    if not _room_has_member(db, room.id, mock.id):
        room_svc.join_room(db, room.id, mock.id)
    return room


@router.post("/demo/setup", response_model=DemoSetupRes)
def setup_demo(
    body: DemoSetupReq | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DemoSetupRes:
    body = body or DemoSetupReq()
    lat = body.latitude if body.latitude is not None else DEMO_LATITUDE
    lng = body.longitude if body.longitude is not None else DEMO_LONGITUDE

    mock = _ensure_mock_user(db, user)
    pet = _ensure_mock_pet(db, mock)
    walk = _ensure_mock_walk(db, mock, pet)
    room = _ensure_demo_room(db, user, mock)
    db.commit()

    return DemoSetupRes(
        mock_user_id=mock.id,
        mock_pet=_to_res(pet),
        mock_walk_session_id=walk.id,
        room_id=room.id,
        room_join_code=room.join_code,
        location=DemoLocation(latitude=lat, longitude=lng, label=DEMO_LABEL),
        mock_location=DemoLocation(
            latitude=MOCK_LATITUDE, longitude=MOCK_LONGITUDE, label=MOCK_LABEL
        ),
    )
