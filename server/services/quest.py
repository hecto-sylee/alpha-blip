"""Quest domain logic (F-12): candidate recommendation, select + lock."""
from __future__ import annotations

import hashlib
from datetime import date

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models import DailyQuest, QuestMission, QuestTemplate

CANDIDATE_COUNT = 3


def _mode_for_scope(scope: str) -> list[str]:
    # user scope shows solo/match packs; room scope shows the room-mode packs.
    if scope == "room":
        return ["walk_friend", "family"]
    return ["solo", "match"]


def missions_for(db: Session, template_id: str) -> list[QuestMission]:
    return (
        db.query(QuestMission)
        .filter(QuestMission.quest_template_id == template_id)
        .order_by(QuestMission.order)
        .all()
    )


def get_daily(db: Session, scope: str, scope_id: str, quest_date: date) -> DailyQuest | None:
    return (
        db.query(DailyQuest)
        .filter(
            DailyQuest.scope == scope,
            DailyQuest.scope_id == scope_id,
            DailyQuest.quest_date == quest_date,
        )
        .first()
    )


def candidates(db: Session, scope: str, scope_id: str, mode: str | None, quest_date: date):
    """Return (locked, daily_quest_or_None, [templates]). Deterministic per
    (scope_id, date) so repeated polls show the same 3 candidates."""
    existing = get_daily(db, scope, scope_id, quest_date)
    if existing and existing.locked:
        return True, existing, [db.get(QuestTemplate, existing.quest_template_id)]

    modes = [mode] if mode else _mode_for_scope(scope)
    pool = (
        db.query(QuestTemplate)
        .filter(QuestTemplate.is_active.is_(True), QuestTemplate.mode.in_(modes))
        .order_by(QuestTemplate.id)
        .all()
    )
    if not pool:
        return False, None, []

    # deterministic shuffle seeded by scope_id+date so polling is stable
    seed = f"{scope_id}:{quest_date.isoformat()}"
    def keyfn(t):
        return hashlib.sha256(f"{seed}:{t.id}".encode()).hexdigest()

    ordered = sorted(pool, key=keyfn)
    return False, None, ordered[:CANDIDATE_COUNT]


def select(db: Session, scope: str, scope_id: str, template_id: str, quest_date: date) -> DailyQuest:
    tpl = db.get(QuestTemplate, template_id)
    if tpl is None:
        raise HTTPException(status_code=404, detail="quest template not found")

    existing = get_daily(db, scope, scope_id, quest_date)
    if existing is not None:
        # room scope: subsequent members share the already-selected quest.
        if scope == "room":
            return existing
        raise HTTPException(status_code=409, detail="quest already selected for the day")

    dq = DailyQuest(
        scope=scope,
        scope_id=scope_id,
        quest_template_id=template_id,
        quest_date=quest_date,
        locked=True,
    )
    db.add(dq)
    db.flush()
    return dq
