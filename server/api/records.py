"""Records (F-10): diary/room walk entries with linked clips + reaction aggregates."""
from __future__ import annotations

import os
import shutil
from collections import Counter
from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from .. import merge as merge_svc
from ..database import SessionLocal
from ..deps import get_current_user, get_db
from ..models import Clip, DailyQuest, MatchSession, Reaction, Record, User
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
from ..services import points as points_svc
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
        merged_ready=bool(rec.merged_path),
        created_at=rec.created_at,
    )


UPLOADS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
MERGED_DIR = os.path.join(UPLOADS_DIR, "merged")


def _build_dual(db: Session, session: MatchSession, out: str) -> bool:
    """매칭 세션 두 유저 클립을 퀘스트별로 vstack(상=user_a/하=user_b). 파트너 칸이 전혀 없으면 False(단일 폴백)."""
    rec_ids = [r.id for r in db.query(Record).filter(Record.match_session_id == session.id).all()]
    if not rec_ids:
        return False
    clips = (
        db.query(Clip)
        .filter(Clip.record_id.in_(rec_ids), Clip.status == "active")
        .order_by(Clip.order.asc(), Clip.created_at.asc())
        .all()
    )
    a_id = session.user_a_id
    b_id = session.user_b_id
    missions: list[str] = []
    by_m: dict[str, dict] = {}
    for c in clips:
        key = c.mission_id or f"solo:{c.id}"
        if key not in by_m:
            by_m[key] = {"top": None, "bottom": None}
            missions.append(key)
        path = os.path.join(UPLOADS_DIR, f"{c.id}.webm")
        if not os.path.exists(path):
            continue
        slot = "top" if c.user_id == a_id else "bottom" if c.user_id == b_id else None
        if slot and not by_m[key][slot]:
            by_m[key][slot] = path
        elif not by_m[key]["top"]:
            by_m[key]["top"] = path
        elif not by_m[key]["bottom"]:
            by_m[key]["bottom"] = path
    scenes = [by_m[m] for m in missions]
    if not any(s["top"] and s["bottom"] for s in scenes):
        return False  # 상대 클립이 전혀 없음(데모 등) → 듀얼 의미 없으니 단일로
    merge_svc.build_dual_video(scenes, out)
    return True


def _merge_record_task(record_id: str) -> None:
    """BackgroundTask: 기록 클립들을 1개 mp4로 합성. 매칭=듀얼 vstack, 솔로=단일 concat."""
    db = SessionLocal()
    try:
        rec = db.get(Record, record_id)
        if rec is None:
            return
        out = os.path.join(MERGED_DIR, f"{record_id}.mp4")
        # 매칭(듀얼): 두 유저 클립을 퀘스트별 vstack. 파트너 클립 없으면 단일 폴백.
        if rec.match_session_id:
            session = db.get(MatchSession, rec.match_session_id)
            if session is not None and _build_dual(db, session, out):
                # 양쪽(요청자·수락자) 기록 모두 '두 명 합성본'을 갖도록 복사+merged_path.
                # 늦게 저장한 쪽의 합성이 돌 때, 먼저 솔로로 떴던 상대 기록도 합성본으로 갱신.
                for r2 in db.query(Record).filter(Record.match_session_id == session.id).all():
                    dst = os.path.join(MERGED_DIR, f"{r2.id}.mp4")
                    if r2.id != record_id:
                        try:
                            shutil.copy2(out, dst)
                        except OSError:
                            continue
                    r2.merged_path = os.path.relpath(dst, UPLOADS_DIR)
                db.commit()
                return
        clips = (
            db.query(Clip)
            .filter(Clip.record_id == record_id, Clip.status == "active")
            .order_by(Clip.order.asc(), Clip.created_at.asc())
            .all()
        )
        paths = [os.path.join(UPLOADS_DIR, f"{c.id}.webm") for c in clips]
        paths = [p for p in paths if os.path.exists(p)]
        if not paths:
            return
        merge_svc.build_record_video(paths, out)
        rec.merged_path = os.path.relpath(out, UPLOADS_DIR)  # "merged/{id}.mp4"
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


@router.post("/records", response_model=RecordCreateRes, status_code=201)
def create_record(
    body: RecordCreateReq,
    background_tasks: BackgroundTasks,
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
    points_awarded = points_svc.award_for_record(
        db, user, clip_count=len(body.clip_ids), is_match=body.match_session_id is not None
    )
    db.commit()
    if body.clip_ids:  # 클립이 있으면 백그라운드로 1개 영상 합성
        background_tasks.add_task(_merge_record_task, rec.id)
    return RecordCreateRes(
        record_id=rec.id, unlocked=unlocked,
        points_awarded=points_awarded, points=user.points,
    )


@router.get("/records/{record_id}/video/download")
def download_record_video(record_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rec = db.get(Record, record_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="record not found")
    if rec.user_id != user.id and rec.visibility != "room":
        raise HTTPException(status_code=403, detail="not allowed")
    if not rec.merged_path:
        raise HTTPException(status_code=409, detail="아직 합성 중이거나 영상이 없어요")
    abs_path = os.path.join(UPLOADS_DIR, rec.merged_path)
    if not os.path.exists(abs_path):
        raise HTTPException(status_code=404, detail="video missing")
    fname = f"letspaw_{rec.walked_at or 'walk'}.mp4"
    return FileResponse(abs_path, media_type="video/mp4", filename=fname)


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
    # 합성 영상 파일 삭제
    if rec.merged_path:
        merged = os.path.join(UPLOADS_DIR, rec.merged_path)
        if os.path.exists(merged):
            try:
                os.remove(merged)
            except OSError:
                pass
    # 이 기록의 클립 파일 + 행 삭제
    for clip in db.query(Clip).filter(Clip.record_id == rec.id).all():
        cp = os.path.join(UPLOADS_DIR, f"{clip.id}.webm")
        if os.path.exists(cp):
            try:
                os.remove(cp)
            except OSError:
                pass
        db.delete(clip)
    db.delete(rec)
    db.commit()
    return {"ok": True}
