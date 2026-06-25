"""Records (F-10): diary/room walk entries with linked clips + reaction aggregates."""
from __future__ import annotations

from collections import Counter
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models import Clip, DailyQuest, Reaction, Record, User
from ..schemas import (
    ClipOut,
    ReactionAgg,
    RecordCreateReq,
    RecordCreateRes,
    RecordListRes,
    RecordOut,
    RecordUpdateReq,
)
from ..services import achievements as ach_svc
from ..services import leagues as league_svc
from ..services import room as room_svc
from ..utils.events import log_event

router = APIRouter(tags=["records"])


def serialize_record(db: Session, rec: Record) -> RecordOut:
    clips = (
        db.query(Clip)
        .filter(Clip.record_id == rec.id, Clip.status == "active")
        .order_by(Clip.order)
        .all()
    )
    counts = Counter(
        r.emoji
        for r in db.query(Reaction).filter(
            Reaction.target_type == "record", Reaction.target_id == rec.id
        )
    )
    return RecordOut(
        id=rec.id,
        user_id=rec.user_id,
        visibility=rec.visibility,
        room_id=rec.room_id,
        match_session_id=rec.match_session_id,
        walked_at=rec.walked_at,
        duration_minutes=rec.duration_minutes,
        distance_meters=rec.distance_meters,
        text=rec.text,
        decoration_json=rec.decoration_json,
        daily_quest_id=rec.daily_quest_id,
        clips=[
            ClipOut(
                id=c.id,
                stream_url=f"/api/clips/{c.id}/stream",
                duration_ms=c.duration_ms,
                order=c.order,
                mission_id=c.mission_id,
                status=c.status,
            )
            for c in clips
        ],
        reactions=[ReactionAgg(emoji=e, count=n) for e, n in counts.items()],
        created_at=rec.created_at,
    )


@router.post("/records", response_model=RecordCreateRes, status_code=201)
def create_record(
    body: RecordCreateReq,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecordCreateRes:
    if body.visibility == "room":
        if not body.room_id:
            raise HTTPException(status_code=400, detail="room_id required for room visibility")
        if not room_svc.is_member(db, body.room_id, user.id):
            raise HTTPException(status_code=403, detail="not a room member")

    # auto-link today's daily quest if present and not provided
    daily_quest_id = body.daily_quest_id
    if daily_quest_id is None and body.walked_at:
        dq = (
            db.query(DailyQuest)
            .filter(
                DailyQuest.scope == "user",
                DailyQuest.scope_id == user.id,
                DailyQuest.quest_date == body.walked_at,
            )
            .first()
        )
        if dq:
            daily_quest_id = dq.id

    rec = Record(
        user_id=user.id,
        walk_session_id=body.walk_session_id,
        match_session_id=body.match_session_id,
        daily_quest_id=daily_quest_id,
        visibility=body.visibility,
        room_id=body.room_id if body.visibility == "room" else None,
        walked_at=body.walked_at,
        duration_minutes=body.duration_minutes,
        distance_meters=body.distance_meters,
        text=body.text,
        decoration_json=body.decoration_json,
    )
    db.add(rec)
    db.flush()

    # attach uploaded clips
    for cid in body.clip_ids:
        clip = db.get(Clip, cid)
        if clip is None or clip.user_id != user.id:
            raise HTTPException(status_code=404, detail=f"clip {cid} not found")
        clip.record_id = rec.id

    log_event(db, "record_save", user_id=user.id, payload={"record_id": rec.id})
    unlocked = ach_svc.evaluate(db, user.id)  # streak/quest/만책/거리 갱신
    league_svc.award_for_record(  # 주간 리그 점수 적립
        db,
        user.id,
        quest_certified=daily_quest_id is not None,
        streak=ach_svc.compute_progress(db, user.id)["streak"],
        when=body.walked_at,
    )
    db.commit()
    return RecordCreateRes(record_id=rec.id, unlocked=unlocked)


@router.get("/records", response_model=RecordListRes)
def list_records(
    from_: date | None = Query(None, alias="from"),
    to: date | None = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecordListRes:
    q = db.query(Record).filter(Record.user_id == user.id)
    if from_:
        q = q.filter(Record.walked_at >= from_)
    if to:
        q = q.filter(Record.walked_at <= to)
    recs = q.order_by(Record.created_at.desc()).all()
    return RecordListRes(records=[serialize_record(db, r) for r in recs])


@router.get("/records/{record_id}", response_model=RecordOut)
def get_record(record_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> RecordOut:
    rec = db.get(Record, record_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="record not found")
    if rec.visibility == "room":
        if not (rec.user_id == user.id or (rec.room_id and room_svc.is_member(db, rec.room_id, user.id))):
            raise HTTPException(status_code=403, detail="not allowed")
    elif rec.user_id != user.id:
        raise HTTPException(status_code=403, detail="not allowed")
    return serialize_record(db, rec)


@router.patch("/records/{record_id}", response_model=RecordOut)
def update_record(
    record_id: str,
    body: RecordUpdateReq,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecordOut:
    rec = db.get(Record, record_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="record not found")
    if rec.user_id != user.id:
        raise HTTPException(status_code=403, detail="not your record")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(rec, key, value)
    db.commit()
    db.refresh(rec)
    return serialize_record(db, rec)


@router.delete("/records/{record_id}")
def delete_record(record_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    rec = db.get(Record, record_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="record not found")
    if rec.user_id != user.id:
        raise HTTPException(status_code=403, detail="not your record")
    for clip in db.query(Clip).filter(Clip.record_id == rec.id):
        clip.status = "hidden"
    db.delete(rec)
    db.commit()
    return {"ok": True}
