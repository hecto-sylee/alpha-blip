"""Leagues (ranking): weekly leaderboard + rollover (manual / auto)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models import User
from ..schemas import LeagueMeRes, LeagueRolloverRes
from ..services import leagues as svc

router = APIRouter(tags=["leagues"])


@router.get("/leagues/me", response_model=LeagueMeRes)
def my_league(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LeagueMeRes:
    res = svc.leaderboard(db, user.id)
    db.commit()  # persist standing creation + any auto-rollover
    return LeagueMeRes(**res)


@router.post("/leagues/rollover", response_model=LeagueRolloverRes)
def rollover(
    week: str | None = Query(None, description="ISO week_key, e.g. 2026-W25; defaults to current week"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LeagueRolloverRes:
    res = svc.rollover(db, user_id=user.id, week=week)
    db.commit()
    return LeagueRolloverRes(**res)
