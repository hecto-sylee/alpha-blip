"""Nearby (F-01) — 현재 broadcast 중인(최근 위치 갱신) 활성 산책 세션을 반경 내에서 보여준다.

실제 좌표 기반(대략적 위치 흐림 제거). 최근 N분 내 위치 갱신된 세션만 → 옛/닫힌 세션 자동 제외.
compute_nearby() 는 REST(/nearby/dogs)와 SSE(/stream)가 공유한다.
"""
from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..api.pets import _to_res
from ..deps import get_current_user, get_db
from ..models import Block, Pet, WalkSession, User, utcnow
from ..schemas import ApproxLocation, NearbyDog, NearbyRes
from ..utils.geo import haversine_meters

router = APIRouter(tags=["nearby"])

FRESH_MINUTES = 10  # 이보다 오래 위치 갱신이 없으면(앱 닫음/옛 세션) 제외


def compute_nearby(
    db: Session, user: User, latitude: float, longitude: float,
    radius_meters: float = 1000, size: str | None = None,
) -> list[NearbyDog]:
    blocked_out = {b.blocked_id for b in db.query(Block).filter(Block.blocker_id == user.id)}
    blocked_in = {b.blocker_id for b in db.query(Block).filter(Block.blocked_id == user.id)}
    excluded = blocked_out | blocked_in | {user.id}

    cutoff = utcnow() - timedelta(minutes=FRESH_MINUTES)
    sessions = (
        db.query(WalkSession)
        .filter(
            WalkSession.status == "active",
            WalkSession.is_location_visible.is_(True),
            WalkSession.lat.isnot(None),
            WalkSession.lng.isnot(None),
            WalkSession.location_updated_at.isnot(None),
            WalkSession.location_updated_at >= cutoff,
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
        dogs.append(
            NearbyDog(
                walk_session_id=ws.id,
                pet=_to_res(pet),
                distance_meters=int(round(dist)),
                approximate_location=ApproxLocation(latitude=ws.lat, longitude=ws.lng),
            )
        )
    dogs.sort(key=lambda d: d.distance_meters)
    return dogs


@router.get("/nearby/dogs", response_model=NearbyRes)
def nearby_dogs(
    latitude: float = Query(...),
    longitude: float = Query(...),
    radius_meters: float = Query(500),
    size: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NearbyRes:
    return NearbyRes(dogs=compute_nearby(db, user, latitude, longitude, radius_meters, size))
