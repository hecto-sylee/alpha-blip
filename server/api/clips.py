"""Clips (F-10): 2-second WebM upload / streaming / hide."""
from __future__ import annotations

import os

import aiofiles
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models import Clip, MatchSession, Record, User, utcnow
from ..schemas import ClipUploadRes
from ..services import room as room_svc
from ..utils.events import log_event

router = APIRouter(tags=["clips"])

UPLOADS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)
CHUNK = 1024 * 256


@router.post("/clips/upload", response_model=ClipUploadRes, status_code=201)
async def upload_clip(
    file: UploadFile = File(...),
    record_id: str | None = Form(None),
    mission_id: str | None = Form(None),
    duration_ms: int | None = Form(None),
    order: int = Form(0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ClipUploadRes:
    clip = Clip(
        record_id=record_id,
        user_id=user.id,
        mission_id=mission_id,
        file_path="",  # set after we know the id
        duration_ms=duration_ms,
        order=order,
        status="active",
    )
    db.add(clip)
    db.flush()

    rel_path = f"uploads/{clip.id}.webm"
    abs_path = os.path.join(UPLOADS_DIR, f"{clip.id}.webm")
    async with aiofiles.open(abs_path, "wb") as f:
        while chunk := await file.read(CHUNK):
            await f.write(chunk)
    clip.file_path = rel_path

    log_event(db, "clip_upload", user_id=user.id, payload={"clip_id": clip.id})
    db.commit()
    return ClipUploadRes(
        clip_id=clip.id, file_path=rel_path, stream_url=f"/api/clips/{clip.id}/stream"
    )


def _can_view(db: Session, clip: Clip, user: User) -> bool:
    if clip.user_id == user.id:
        return True
    rec = db.get(Record, clip.record_id) if clip.record_id else None
    if rec is None:
        return False
    # 매칭 동행자: 상대의 *해당 match_session 에 연결된* 기록 클립만 열람 허용 (W5/O2).
    # 일반 diary 클립은 여전히 owner 전용 — 범위를 매칭 record 클립에 한정한다.
    if rec.match_session_id:
        session = db.get(MatchSession, rec.match_session_id)
        if session and user.id in (session.user_a_id, session.user_b_id):
            return True
    if rec.visibility == "room" and rec.room_id:
        return room_svc.is_member(db, rec.room_id, user.id)
    return rec.user_id == user.id


@router.get("/clips/{clip_id}/stream")
def stream_clip(
    clip_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    clip = db.get(Clip, clip_id)
    if clip is None or clip.status != "active":
        raise HTTPException(status_code=404, detail="clip not found")
    if not _can_view(db, clip, user):
        raise HTTPException(status_code=403, detail="not allowed")

    abs_path = os.path.join(UPLOADS_DIR, f"{clip.id}.webm")
    if not os.path.exists(abs_path):
        raise HTTPException(status_code=404, detail="file missing")
    file_size = os.path.getsize(abs_path)
    range_header = request.headers.get("range")

    if range_header:
        # bytes=start-end
        units, _, rng = range_header.partition("=")
        start_s, _, end_s = rng.partition("-")
        start = int(start_s) if start_s else 0
        end = int(end_s) if end_s else file_size - 1
        end = min(end, file_size - 1)
        length = end - start + 1

        def iter_range():
            with open(abs_path, "rb") as fh:
                fh.seek(start)
                remaining = length
                while remaining > 0:
                    data = fh.read(min(CHUNK, remaining))
                    if not data:
                        break
                    remaining -= len(data)
                    yield data

        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(length),
        }
        return StreamingResponse(iter_range(), status_code=206, media_type="video/webm", headers=headers)

    def iter_full():
        with open(abs_path, "rb") as fh:
            while data := fh.read(CHUNK):
                yield data

    return StreamingResponse(
        iter_full(),
        media_type="video/webm",
        headers={"Accept-Ranges": "bytes", "Content-Length": str(file_size)},
    )


@router.delete("/clips/{clip_id}")
def delete_clip(clip_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    clip = db.get(Clip, clip_id)
    if clip is None:
        raise HTTPException(status_code=404, detail="clip not found")
    if clip.user_id != user.id:
        raise HTTPException(status_code=403, detail="not your clip")
    # same-day only
    if clip.created_at.date() != utcnow().date():
        raise HTTPException(status_code=403, detail="can only hide same-day clips")
    clip.status = "hidden"
    db.commit()
    return {"ok": True}
