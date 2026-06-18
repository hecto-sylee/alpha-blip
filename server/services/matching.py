"""Matching domain logic (F-03/04/05): request conflicts, expiry, session creation."""
from __future__ import annotations

from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models import (
    Block,
    MatchLog,
    MatchRequest,
    MatchSession,
    User,
    WalkSession,
    utcnow,
)

REQUEST_TTL_MINUTES = 2


def _is_blocked(db: Session, a: str, b: str) -> bool:
    q = db.query(Block).filter(
        ((Block.blocker_id == a) & (Block.blocked_id == b))
        | ((Block.blocker_id == b) & (Block.blocked_id == a))
    )
    return db.query(q.exists()).scalar()


def _is_expired(req: MatchRequest) -> bool:
    return req.expires_at is not None and req.expires_at < utcnow()


def create_request(db: Session, requester_id: str, receiver_walk_session_id: str) -> MatchRequest:
    receiver_ws = db.get(WalkSession, receiver_walk_session_id)
    if receiver_ws is None or receiver_ws.status != "active":
        raise HTTPException(status_code=404, detail="receiver walk session not found")
    if receiver_ws.user_id == requester_id:
        raise HTTPException(status_code=400, detail="cannot request yourself")
    if _is_blocked(db, requester_id, receiver_ws.user_id):
        raise HTTPException(status_code=403, detail="blocked relationship")

    # requester's own active walk session (most recent)
    requester_ws = (
        db.query(WalkSession)
        .filter(WalkSession.user_id == requester_id, WalkSession.status == "active")
        .order_by(WalkSession.started_at.desc())
        .first()
    )

    req = MatchRequest(
        requester_id=requester_id,
        receiver_id=receiver_ws.user_id,
        requester_walk_session_id=requester_ws.id if requester_ws else None,
        receiver_walk_session_id=receiver_ws.id,
        pet_a_id=requester_ws.pet_id if requester_ws else None,
        pet_b_id=receiver_ws.pet_id,
        status="pending",
        expires_at=utcnow() + timedelta(minutes=REQUEST_TTL_MINUTES),
    )
    db.add(req)
    db.flush()
    receiver = db.get(User, receiver_ws.user_id)
    if receiver and receiver.is_mock:
        accept_request(db, req.id, receiver.id)
    return req


def list_incoming(db: Session, receiver_id: str) -> list[MatchRequest]:
    reqs = (
        db.query(MatchRequest)
        .filter(MatchRequest.receiver_id == receiver_id, MatchRequest.status == "pending")
        .order_by(MatchRequest.created_at.desc())
        .all()
    )
    fresh = []
    for r in reqs:
        if _is_expired(r):
            r.status = "expired"  # lazy expiry on read
            continue
        fresh.append(r)
    return fresh


def accept_request(db: Session, request_id: str, receiver_id: str) -> MatchSession:
    req = db.get(MatchRequest, request_id)
    if req is None:
        raise HTTPException(status_code=404, detail="request not found")
    if req.receiver_id != receiver_id:
        raise HTTPException(status_code=403, detail="not your request")
    if req.status != "pending":
        raise HTTPException(status_code=409, detail=f"request is {req.status}")
    if _is_expired(req):
        req.status = "expired"
        raise HTTPException(status_code=409, detail="request expired")

    req.status = "accepted"
    session = MatchSession(
        match_request_id=req.id,
        user_a_id=req.requester_id,
        user_b_id=req.receiver_id,
        pet_a_id=req.pet_a_id,
        pet_b_id=req.pet_b_id,
        status="active",
    )
    db.add(session)

    # auto-expire other pending requests to the same receiver
    others = (
        db.query(MatchRequest)
        .filter(
            MatchRequest.receiver_id == receiver_id,
            MatchRequest.status == "pending",
            MatchRequest.id != req.id,
        )
        .all()
    )
    for o in others:
        o.status = "expired"

    db.flush()
    return session


def end_session(db: Session, session_id: str, user_id: str, duration_minutes=None, distance_meters=None) -> MatchLog:
    session = db.get(MatchSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    if user_id not in (session.user_a_id, session.user_b_id):
        raise HTTPException(status_code=403, detail="not a participant")

    if session.status == "ended":
        existing = db.query(MatchLog).filter(MatchLog.match_session_id == session.id).first()
        if existing:
            return existing

    session.status = "ended"
    session.ended_at = utcnow()

    # meet_count: count prior logs between these two users + 1
    prior = (
        db.query(MatchLog)
        .filter(
            ((MatchLog.user_a_id == session.user_a_id) & (MatchLog.user_b_id == session.user_b_id))
            | ((MatchLog.user_a_id == session.user_b_id) & (MatchLog.user_b_id == session.user_a_id))
        )
        .count()
    )

    log = MatchLog(
        match_session_id=session.id,
        user_a_id=session.user_a_id,
        user_b_id=session.user_b_id,
        pet_a_id=session.pet_a_id,
        pet_b_id=session.pet_b_id,
        walked_at=utcnow().date(),
        duration_minutes=duration_minutes,
        distance_meters=distance_meters,
        meet_count=prior + 1,
    )
    db.add(log)
    db.flush()
    return log
