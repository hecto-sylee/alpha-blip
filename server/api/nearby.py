"""Nearby (F-01) — app-level Haversine radius filter over active walk sessions."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..api.pets import _to_res
from ..deps import get_current_user, get_db
from ..models import Block, Pet, WalkSession, User
from ..schemas import ApproxLocation, NearbyDog, NearbyRes
from ..utils.geo import approximate_location, haversine_meters

router = APIRouter(tags=["nearby"])


@router.get("/nearby/dogs", response_model=NearbyRes)
def nearby_dogs(
    latitude: float = Query(...),
    longitude: float = Query(...),
    radius_meters: float = Query(500),
    size: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NearbyRes:
    # Two-way block exclusion.
    blocked_out = {b.blocked_id for b in db.query(Block).filter(Block.blocker_id == user.id)}
    blocked_in = {b.blocker_id for b in db.query(Block).filter(Block.blocked_id == user.id)}
    excluded = blocked_out | blocked_in | {user.id}

    sessions = (
        db.query(WalkSession)
        .filter(
            WalkSession.status == "active",
            WalkSession.is_location_visible.is_(True),
            WalkSession.lat.isnot(None),
            WalkSession.lng.isnot(None),
        )
        .all()
    )

    dogs: list[NearbyDog] = []
    for ws in sessions:
        if ws.user_id in excluded:
            continue
        owner = db.get(User, ws.user_id)
        if owner is None:
            continue
        if owner.is_mock and owner.auth_token != f"demo-mock:{user.id}":
            continue
        dist = haversine_meters(latitude, longitude, ws.lat, ws.lng)
        if dist > radius_meters:
            continue
        pet = db.get(Pet, ws.pet_id)
        if pet is None:
            continue
        if size and pet.size != size:
            continue
        alat, alng = approximate_location(ws.lat, ws.lng, seed=ws.id)
        dogs.append(
            NearbyDog(
                walk_session_id=ws.id,
                pet=_to_res(pet),
                distance_meters=int(round(dist)),
                approximate_location=ApproxLocation(latitude=alat, longitude=alng),
            )
        )

    dogs.sort(key=lambda d: d.distance_meters)
    return NearbyRes(dogs=dogs)
