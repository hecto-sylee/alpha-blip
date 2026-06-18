"""Room domain logic (F-11): join-code issue, membership, dedup."""
from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models import Room, RoomMember
from ..utils.codes import gen_join_code


def _unique_code(db: Session) -> str:
    for _ in range(20):
        code = gen_join_code(6)
        if db.query(Room).filter(Room.join_code == code).first() is None:
            return code
    raise HTTPException(status_code=500, detail="could not allocate join code")


def create_room(db: Session, owner_id: str, name: str, mode: str) -> Room:
    room = Room(name=name, mode=mode, join_code=_unique_code(db), owner_id=owner_id)
    db.add(room)
    db.flush()
    db.add(RoomMember(room_id=room.id, user_id=owner_id, status="joined"))
    db.flush()
    return room


def active_members(db: Session, room_id: str) -> list[RoomMember]:
    return (
        db.query(RoomMember)
        .filter(RoomMember.room_id == room_id, RoomMember.status == "joined")
        .all()
    )


def join_room(db: Session, room_id: str, user_id: str) -> RoomMember:
    room = db.get(Room, room_id)
    if room is None or room.status == "deleted":
        raise HTTPException(status_code=404, detail="room not found")

    existing = (
        db.query(RoomMember)
        .filter(RoomMember.room_id == room_id, RoomMember.user_id == user_id)
        .first()
    )
    if existing is not None:
        if existing.status != "joined":
            existing.status = "joined"  # rejoin
            db.flush()
        return existing  # dedup: return existing membership

    if len(active_members(db, room_id)) >= room.max_members:
        raise HTTPException(status_code=409, detail="room is full")

    member = RoomMember(room_id=room_id, user_id=user_id, status="joined")
    db.add(member)
    db.flush()
    return member


def leave_room(db: Session, room_id: str, user_id: str) -> None:
    member = (
        db.query(RoomMember)
        .filter(RoomMember.room_id == room_id, RoomMember.user_id == user_id)
        .first()
    )
    if member is None:
        raise HTTPException(status_code=404, detail="not a member")
    member.status = "left"
    db.flush()
    if not active_members(db, room_id):
        room = db.get(Room, room_id)
        if room:
            room.status = "deleted"


def is_member(db: Session, room_id: str, user_id: str) -> bool:
    m = (
        db.query(RoomMember)
        .filter(
            RoomMember.room_id == room_id,
            RoomMember.user_id == user_id,
            RoomMember.status == "joined",
        )
        .first()
    )
    return m is not None
