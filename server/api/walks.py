"""Walks (F-01) — personal walk sessions + location updates."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models import Pet, WalkSession, User, utcnow
from ..schemas import LocationReq, WalkEndReq, WalkStartReq, WalkStartRes
from ..utils.events import log_event

router = APIRouter(tags=["walks"])


@router.post("/walks/start", response_model=WalkStartRes, status_code=201)
def start_walk(
    body: WalkStartReq,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WalkStartRes:
    # Profile must exist (03 spec: unregistered -> 403, register prompt).
    pets = db.query(Pet).filter(Pet.user_id == user.id).count()
    if pets == 0:
        raise HTTPException(status_code=403, detail="register a pet first")

    pet = db.get(Pet, body.pet_id)
    if pet is None or pet.user_id != user.id:
        raise HTTPException(status_code=404, detail="pet not found")

    ws = WalkSession(
        user_id=user.id,
        pet_id=body.pet_id,
        status="active",
        lat=body.latitude,
        lng=body.longitude,
        location_updated_at=utcnow() if body.latitude is not None else None,
        is_location_visible=True,
    )
    db.add(ws)
    db.flush()
    log_event(db, "walk_start", user_id=user.id, payload={"walk_session_id": ws.id})
    db.commit()
    return WalkStartRes(walk_session_id=ws.id, started_at=ws.started_at)


@router.patch("/walks/{walk_id}/location")
def update_location(
    walk_id: str,
    body: LocationReq,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    ws = db.get(WalkSession, walk_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="walk session not found")
    if ws.user_id != user.id:
        raise HTTPException(status_code=403, detail="not your walk session")
    ws.lat = body.latitude
    ws.lng = body.longitude
    ws.location_updated_at = utcnow()
    db.commit()
    return {"ok": True}


@router.post("/walks/{walk_id}/end")
def end_walk(
    walk_id: str,
    body: WalkEndReq,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    ws = db.get(WalkSession, walk_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="walk session not found")
    if ws.user_id != user.id:
        raise HTTPException(status_code=403, detail="not your walk session")
    ws.status = "closed"
    ws.ended_at = body.ended_at or utcnow()
    log_event(db, "walk_end", user_id=user.id, payload={"walk_session_id": ws.id})
    db.commit()
    return {"ok": True, "walk_session_id": ws.id}
