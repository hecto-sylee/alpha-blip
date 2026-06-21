"""Matches (F-03/04/05): requests, sessions, logs."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models import MatchLog, MatchRequest, MatchSession, Pet, User
from ..schemas import (
    AcceptRes,
    IncomingRequest,
    IncomingRes,
    MatchEndReq,
    MatchEndRes,
    MatchRequestReq,
    MatchRequestRes,
    MatchSessionRes,
)
from ..services import achievements as ach_svc
from ..services import matching
from ..utils.events import log_event

router = APIRouter(tags=["matches"])


@router.post("/match-requests", response_model=MatchRequestRes, status_code=201)
def create_match_request(
    body: MatchRequestReq,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MatchRequestRes:
    req = matching.create_request(db, user.id, body.receiver_walk_session_id)
    log_event(db, "match_request", user_id=user.id, payload={"match_request_id": req.id})
    db.commit()
    return MatchRequestRes(match_request_id=req.id, expires_at=req.expires_at)


@router.get("/match-requests/incoming", response_model=IncomingRes)
def incoming(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> IncomingRes:
    reqs = matching.list_incoming(db, user.id)
    out = []
    for r in reqs:
        requester = db.get(User, r.requester_id)
        pet = db.get(Pet, r.pet_a_id) if r.pet_a_id else None
        out.append(
            IncomingRequest(
                id=r.id,
                requester={"nickname": requester.nickname if requester else None},
                pet={"name": pet.name, "breed": pet.breed} if pet else None,
                status=r.status,
                expires_at=r.expires_at,
                created_at=r.created_at,
            )
        )
    db.commit()  # persist lazy-expiry side effects
    return IncomingRes(requests=out)


@router.patch("/match-requests/{request_id}/accept", response_model=AcceptRes)
def accept(request_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> AcceptRes:
    session = matching.accept_request(db, request_id, user.id)
    log_event(db, "match_accept", user_id=user.id, payload={"match_session_id": session.id})
    db.commit()
    return AcceptRes(match_session_id=session.id)


@router.get("/match-requests/{request_id}")
def get_request(request_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    """요청 발신자/수신자가 상태를 폴링한다(04_frontend_spec 핵심구현 3).
    accepted면 생성된 match_session_id를 함께 반환. 만료는 조회 시점 lazy 처리."""
    req = db.get(MatchRequest, request_id)
    if req is None:
        raise HTTPException(status_code=404, detail="request not found")
    if user.id not in (req.requester_id, req.receiver_id):
        raise HTTPException(status_code=403, detail="not your request")
    if req.status == "pending" and req.expires_at is not None and req.expires_at < matching.utcnow():
        req.status = "expired"
        db.commit()
    session = db.query(MatchSession).filter(MatchSession.match_request_id == req.id).first()
    return {
        "id": req.id,
        "status": req.status,
        "expires_at": req.expires_at.isoformat() if req.expires_at else None,
        "match_session_id": session.id if session else None,
    }


@router.patch("/match-requests/{request_id}/reject")
def reject(request_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    req = db.get(MatchRequest, request_id)
    if req is None:
        raise HTTPException(status_code=404, detail="request not found")
    if req.receiver_id != user.id:
        raise HTTPException(status_code=403, detail="not your request")
    req.status = "rejected"
    db.commit()
    return {"ok": True}


@router.delete("/match-requests/{request_id}")
def cancel(request_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    req = db.get(MatchRequest, request_id)
    if req is None:
        raise HTTPException(status_code=404, detail="request not found")
    if req.requester_id != user.id:
        raise HTTPException(status_code=403, detail="only requester can cancel")
    req.status = "cancelled"
    db.commit()
    return {"ok": True}


@router.get("/match-sessions/{session_id}", response_model=MatchSessionRes)
def get_session(session_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> MatchSessionRes:
    session = db.get(MatchSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    if user.id not in (session.user_a_id, session.user_b_id):
        raise HTTPException(status_code=403, detail="not a participant")
    partner_id = session.user_b_id if user.id == session.user_a_id else session.user_a_id
    partner_pet_id = session.pet_b_id if user.id == session.user_a_id else session.pet_a_id
    partner = db.get(User, partner_id)
    pet = db.get(Pet, partner_pet_id) if partner_pet_id else None
    return MatchSessionRes(
        id=session.id,
        status=session.status,
        partner={
            "nickname": partner.nickname if partner else None,
            "pet": {"name": pet.name, "breed": pet.breed} if pet else None,
        },
        started_at=session.started_at,
    )


@router.post("/match-sessions/{session_id}/end", response_model=MatchEndRes)
def end_session(
    session_id: str,
    body: MatchEndReq | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MatchEndRes:
    body = body or MatchEndReq()
    log = matching.end_session(
        db, session_id, user.id, duration_minutes=body.duration_minutes, distance_meters=body.distance_meters
    )
    log_event(db, "match_end", user_id=user.id, payload={"match_log_id": log.id})
    unlocked = ach_svc.evaluate(db, user.id)  # 친구 N회 산책 마일스톤 갱신
    db.commit()
    return MatchEndRes(match_log_id=log.id, unlocked=unlocked)


@router.post("/match-sessions/{session_id}/cancel")
def cancel_session(session_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    session = db.get(MatchSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    if user.id not in (session.user_a_id, session.user_b_id):
        raise HTTPException(status_code=403, detail="not a participant")
    session.status = "cancelled"
    session.ended_at = matching.utcnow()
    db.commit()
    return {"ok": True}


@router.get("/match-logs")
def list_logs(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    logs = (
        db.query(MatchLog)
        .filter((MatchLog.user_a_id == user.id) | (MatchLog.user_b_id == user.id))
        .order_by(MatchLog.created_at.desc())
        .all()
    )
    out = []
    for log in logs:
        partner_pet_id = log.pet_b_id if log.user_a_id == user.id else log.pet_a_id
        pet = db.get(Pet, partner_pet_id) if partner_pet_id else None
        out.append(
            {
                "id": log.id,
                "partner_pet": {"name": pet.name, "breed": pet.breed, "photo_url": pet.photo_url} if pet else None,
                "walked_at": log.walked_at.isoformat() if log.walked_at else None,
                "duration_minutes": log.duration_minutes,
                "meet_count": log.meet_count,
            }
        )
    return {"logs": out}
