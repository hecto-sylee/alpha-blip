"""Reactions (F-11): emoji toggle on records/clips shared in a room."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models import Clip, Reaction, Record, User
from ..schemas import ReactionReq
from ..services import room as room_svc
from ..utils.events import log_event

router = APIRouter(tags=["reactions"])

ALLOWED = {"❤️", "😂", "🔥", "👍", "😮"}


def _resolve_record(db: Session, target_type: str, target_id: str) -> Record | None:
    if target_type == "record":
        return db.get(Record, target_id)
    if target_type == "clip":
        clip = db.get(Clip, target_id)
        if clip and clip.record_id:
            return db.get(Record, clip.record_id)
    return None


@router.post("/reactions")
def toggle_reaction(
    body: ReactionReq,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if body.target_type not in ("record", "clip"):
        raise HTTPException(status_code=400, detail="invalid target_type")
    if body.emoji not in ALLOWED:
        raise HTTPException(status_code=400, detail="invalid emoji")

    # Must target something shared in a room the user belongs to.
    rec = _resolve_record(db, body.target_type, body.target_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="target not found")
    if rec.visibility != "room" or not rec.room_id or not room_svc.is_member(db, rec.room_id, user.id):
        raise HTTPException(status_code=403, detail="can only react to room-shared content")

    existing = (
        db.query(Reaction)
        .filter(
            Reaction.target_type == body.target_type,
            Reaction.target_id == body.target_id,
            Reaction.user_id == user.id,
            Reaction.emoji == body.emoji,
        )
        .first()
    )
    if existing is not None:
        db.delete(existing)
        db.commit()
        return {"toggled": "removed"}

    db.add(
        Reaction(
            target_type=body.target_type,
            target_id=body.target_id,
            user_id=user.id,
            emoji=body.emoji,
        )
    )
    log_event(db, "reaction", user_id=user.id, payload={"target_id": body.target_id, "emoji": body.emoji})
    db.commit()
    return {"toggled": "added"}
