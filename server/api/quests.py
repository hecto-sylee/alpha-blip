"""Quests (F-12): candidates, select+lock, today, admin."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models import DailyQuest, QuestTemplate, User, utcnow
from ..schemas import (
    CandidatesRes,
    MissionOut,
    QuestCandidate,
    QuestSelectReq,
    QuestSelectRes,
)
from ..services import quest as quest_svc
from ..services import room as room_svc
from ..utils.events import log_event

router = APIRouter(tags=["quests"])


def _candidate(db: Session, tpl: QuestTemplate) -> QuestCandidate:
    missions = quest_svc.missions_for(db, tpl.id)
    return QuestCandidate(
        quest_template_id=tpl.id,
        title=tpl.title,
        description=tpl.description,
        missions=[MissionOut(id=m.id, order=m.order, title=m.title, hint=m.hint) for m in missions],
    )


@router.get("/quests/candidates", response_model=CandidatesRes)
def candidates(
    scope: str = Query("user"),
    scope_id: str | None = Query(None),
    mode: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CandidatesRes:
    sid = scope_id or user.id
    today = utcnow().date()
    locked, _daily, templates = quest_svc.candidates(db, scope, sid, mode, today)
    return CandidatesRes(locked=locked, candidates=[_candidate(db, t) for t in templates if t])


@router.post("/quests/select", response_model=QuestSelectRes, status_code=201)
def select(
    body: QuestSelectReq,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QuestSelectRes:
    if body.scope == "room" and not room_svc.is_member(db, body.scope_id, user.id):
        raise HTTPException(status_code=403, detail="not a room member")
    dq = quest_svc.select(db, body.scope, body.scope_id, body.quest_template_id, body.quest_date)
    log_event(db, "quest_select", user_id=user.id, payload={"daily_quest_id": dq.id})
    db.commit()
    return QuestSelectRes(daily_quest_id=dq.id, locked=dq.locked)


@router.get("/quests/today")
def today(
    scope: str = Query("user"),
    scope_id: str | None = Query(None),
    date_: date | None = Query(None, alias="date"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    sid = scope_id or user.id
    qd = date_ or utcnow().date()
    dq = quest_svc.get_daily(db, scope, sid, qd)
    if dq is None:
        return {"locked": False, "quest": None}
    tpl = db.get(QuestTemplate, dq.quest_template_id)
    return {
        "locked": dq.locked,
        "daily_quest_id": dq.id,
        "quest": _candidate(db, tpl).model_dump() if tpl else None,
    }


# --- admin (simple) ---
@router.get("/admin/quests")
def admin_list(db: Session = Depends(get_db)) -> dict:
    rows = db.query(QuestTemplate).order_by(QuestTemplate.mode, QuestTemplate.title).all()
    return {
        "quests": [
            {"id": t.id, "mode": t.mode, "title": t.title, "description": t.description, "is_active": t.is_active}
            for t in rows
        ]
    }


@router.patch("/admin/quests/{template_id}")
def admin_update(template_id: str, body: dict, db: Session = Depends(get_db)) -> dict:
    tpl = db.get(QuestTemplate, template_id)
    if tpl is None:
        raise HTTPException(status_code=404, detail="not found")
    for field in ("title", "description", "is_active"):
        if field in body:
            setattr(tpl, field, body[field])
    db.commit()
    return {"ok": True}
