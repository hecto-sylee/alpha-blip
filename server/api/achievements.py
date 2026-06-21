"""Achievements (badges): grid listing + manual re-evaluation."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models import User
from ..schemas import AchievementEvaluateRes, AchievementListRes
from ..services import achievements as svc

router = APIRouter(tags=["achievements"])


@router.get("/achievements", response_model=AchievementListRes)
def list_achievements(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AchievementListRes:
    # Viewing the grid also persists any badge whose threshold is already met
    # (covers progress earned via paths that don't run evaluate, e.g. the
    # partner side of a match).
    if svc.evaluate(db, user.id):
        db.commit()
    return AchievementListRes(**svc.list_for_user(db, user.id))


@router.post("/achievements/evaluate", response_model=AchievementEvaluateRes)
def evaluate_achievements(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AchievementEvaluateRes:
    newly = svc.evaluate(db, user.id)
    if newly:
        db.commit()
    return AchievementEvaluateRes(unlocked=newly)
