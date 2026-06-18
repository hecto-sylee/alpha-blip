"""Rooms (F-11): create, join by code, detail timeline, leave, my rooms."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..api.records import serialize_record
from ..deps import get_current_user, get_db
from ..models import DailyQuest, QuestTemplate, Record, Room, RoomMember, User, utcnow
from ..schemas import RoomCardOut, RoomCreateReq, RoomCreateRes
from ..services import quest as quest_svc
from ..services import room as room_svc
from ..utils.events import log_event

router = APIRouter(tags=["rooms"])


@router.post("/rooms", response_model=RoomCreateRes, status_code=201)
def create_room(
    body: RoomCreateReq,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RoomCreateRes:
    room = room_svc.create_room(db, user.id, body.name, body.mode)
    log_event(db, "room_create", user_id=user.id, payload={"room_id": room.id})
    db.commit()
    return RoomCreateRes(room_id=room.id, join_code=room.join_code)


@router.get("/rooms")
def my_rooms(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    memberships = (
        db.query(RoomMember)
        .filter(RoomMember.user_id == user.id, RoomMember.status == "joined")
        .all()
    )
    cards = []
    for m in memberships:
        room = db.get(Room, m.room_id)
        if room is None or room.status == "deleted":
            continue
        cards.append(
            RoomCardOut(
                room_id=room.id,
                name=room.name,
                mode=room.mode,
                join_code=room.join_code,
                member_count=len(room_svc.active_members(db, room.id)),
            ).model_dump()
        )
    return {"rooms": cards}


@router.get("/rooms/code/{join_code}")
def get_by_code(join_code: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    room = db.query(Room).filter(Room.join_code == join_code.upper(), Room.status == "active").first()
    if room is None:
        raise HTTPException(status_code=404, detail="room not found")
    return {
        "room_id": room.id,
        "name": room.name,
        "mode": room.mode,
        "join_code": room.join_code,
        "member_count": len(room_svc.active_members(db, room.id)),
    }


@router.post("/rooms/{room_id}/join")
def join_room(room_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    member = room_svc.join_room(db, room_id, user.id)
    log_event(db, "room_join", user_id=user.id, payload={"room_id": room_id})
    db.commit()
    return {"ok": True, "member_id": member.id, "status": member.status}


@router.post("/rooms/{room_id}/leave")
def leave_room(room_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    room_svc.leave_room(db, room_id, user.id)
    db.commit()
    return {"ok": True}


@router.get("/rooms/{room_id}")
def room_detail(room_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    room = db.get(Room, room_id)
    if room is None or room.status == "deleted":
        raise HTTPException(status_code=404, detail="room not found")
    if not room_svc.is_member(db, room_id, user.id):
        raise HTTPException(status_code=403, detail="not a room member")

    members = []
    for m in room_svc.active_members(db, room_id):
        u = db.get(User, m.user_id)
        members.append({"user_id": m.user_id, "nickname": u.nickname if u else None})

    # today's room quest
    today = utcnow().date()
    dq = quest_svc.get_daily(db, "room", room_id, today)
    room_quest = None
    if dq:
        tpl = db.get(QuestTemplate, dq.quest_template_id)
        room_quest = {
            "daily_quest_id": dq.id,
            "locked": dq.locked,
            "title": tpl.title if tpl else None,
        }

    # shared records timeline (room_id) with clips + reaction aggregates
    recs = (
        db.query(Record)
        .filter(Record.room_id == room_id, Record.visibility == "room")
        .order_by(Record.created_at.desc())
        .all()
    )
    timeline = [serialize_record(db, r).model_dump() for r in recs]

    return {
        "room_id": room.id,
        "name": room.name,
        "mode": room.mode,
        "join_code": room.join_code,
        "members": members,
        "today_quest": room_quest,
        "timeline": timeline,
    }
