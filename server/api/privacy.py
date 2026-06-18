"""Privacy (F-09): block / unblock / report."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models import Block, Report, User
from ..schemas import BlockReq, ReportReq
from ..utils.events import log_event

router = APIRouter(tags=["privacy"])


@router.post("/privacy/block", status_code=201)
def block_user(
    body: BlockReq,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if body.target_user_id == user.id:
        raise HTTPException(status_code=400, detail="cannot block yourself")
    target = db.get(User, body.target_user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="user not found")

    existing = (
        db.query(Block)
        .filter(Block.blocker_id == user.id, Block.blocked_id == body.target_user_id)
        .first()
    )
    if existing is not None:
        return {"ok": True, "already_blocked": True}

    db.add(Block(blocker_id=user.id, blocked_id=body.target_user_id))
    log_event(db, "block", user_id=user.id, payload={"target_user_id": body.target_user_id})
    db.commit()
    return {"ok": True}


@router.delete("/privacy/block/{user_id}")
def unblock_user(
    user_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    block = (
        db.query(Block)
        .filter(Block.blocker_id == user.id, Block.blocked_id == user_id)
        .first()
    )
    if block is None:
        raise HTTPException(status_code=404, detail="block not found")
    db.delete(block)
    log_event(db, "unblock", user_id=user.id, payload={"target_user_id": user_id})
    db.commit()
    return {"ok": True}


@router.post("/privacy/report", status_code=201)
def report_user(
    body: ReportReq,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if body.target_user_id == user.id:
        raise HTTPException(status_code=400, detail="cannot report yourself")
    target = db.get(User, body.target_user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="user not found")

    reason = body.reason
    if body.context:
        reason = f"{reason or ''} | context: {body.context}".strip(" |")

    report = Report(reporter_id=user.id, reported_id=body.target_user_id, reason=reason)
    db.add(report)
    log_event(db, "report", user_id=user.id, payload={"target_user_id": body.target_user_id})
    db.commit()
    return {"ok": True, "report_id": report.id}
