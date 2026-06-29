"""Matches (F-03/04/05): requests, sessions, logs."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models import Clip, MatchLog, MatchRequest, MatchSession, Pet, Record, User, WalkSession
from ..schemas import (
    AcceptRes,
    ClipOut,
    IncomingRequest,
    IncomingRes,
    MatchEndReq,
    MatchEndRes,
    MatchRecordOut,
    MatchRequestReq,
    MatchRequestRes,
    MatchSessionRecordsRes,
    MatchSessionRes,
)
from ..services import achievements as ach_svc
from ..services import matching
from ..utils.events import log_event
from ..utils.jsonx import loads_list

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
                pet={
                    "id": pet.id,
                    "name": pet.name,
                    "breed": pet.breed,
                    "size": pet.size,
                    "personality_tags": loads_list(pet.personality_tags),
                }
                if pet
                else None,
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


def _session_res(session: MatchSession, user: User, db: Session) -> MatchSessionRes:
    partner_id = session.user_b_id if user.id == session.user_a_id else session.user_a_id
    partner_pet_id = session.pet_b_id if user.id == session.user_a_id else session.pet_a_id
    partner = db.get(User, partner_id)
    pet = db.get(Pet, partner_pet_id) if partner_pet_id else None
    i_met = session.a_met if user.id == session.user_a_id else session.b_met
    # 상대의 현재 실제 위치(활성 walk 세션) — 수락 후 서로 실시간 위치 표시용
    pws = (
        db.query(WalkSession)
        .filter(
            WalkSession.user_id == partner_id,
            WalkSession.status == "active",
            WalkSession.lat.isnot(None),
            WalkSession.lng.isnot(None),
        )
        # 실제 broadcast 중인 위치와 일치하도록 가장 최근 '위치 갱신' 세션을 고른다
        # (started_at 기준이면 broadcast 중인 세션과 다른 옛 세션을 집을 수 있음).
        .order_by(WalkSession.location_updated_at.desc())
        .first()
    )
    return MatchSessionRes(
        id=session.id,
        status=session.status,
        partner={
            "nickname": partner.nickname if partner else None,
            "pet": {
                "id": pet.id, "name": pet.name, "breed": pet.breed, "size": pet.size,
                "personality_tags": loads_list(pet.personality_tags),
            } if pet else None,
        },
        started_at=session.started_at,
        a_met=session.a_met, b_met=session.b_met,
        both_met=bool(session.a_met and session.b_met), i_met=bool(i_met),
        my_position="top" if user.id == session.user_a_id else "bottom",  # 합성: top=user_a/bottom=user_b
        partner_lat=pws.lat if pws else None,
        partner_lng=pws.lng if pws else None,
    )


@router.get("/match-sessions/{session_id}", response_model=MatchSessionRes)
def get_session(session_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> MatchSessionRes:
    session = db.get(MatchSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    if user.id not in (session.user_a_id, session.user_b_id):
        raise HTTPException(status_code=403, detail="not a participant")
    return _session_res(session, user, db)


@router.post("/match-sessions/{session_id}/met", response_model=MatchSessionRes)
def mark_met(session_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> MatchSessionRes:
    """만남 게이트: 내 met 표시. 양쪽 met이면 status=walking. (데모 mock 상대는 자동 met)"""
    session = db.get(MatchSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    if user.id not in (session.user_a_id, session.user_b_id):
        raise HTTPException(status_code=403, detail="not a participant")
    # 요청자/수락자 각자 자기 met만 표시. 양쪽 모두 눌러야 진행(자동 met 없음).
    if user.id == session.user_a_id:
        session.a_met = True
    else:
        session.b_met = True
    if session.a_met and session.b_met and session.status == "active":
        session.status = "walking"
    db.commit()
    return _session_res(session, user, db)


@router.get("/match-sessions/{session_id}/records", response_model=MatchSessionRecordsRes)
def get_session_records(
    session_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MatchSessionRecordsRes:
    """매칭 산책 양측의 기록 영상 조회 (W5). 참여자 전용.
    세션에 연결된 Record 를 user 별로 분리해 각 active 클립을 직렬화한다."""
    session = db.get(MatchSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    if user.id not in (session.user_a_id, session.user_b_id):
        raise HTTPException(status_code=403, detail="not a participant")
    partner_id = session.user_b_id if user.id == session.user_a_id else session.user_a_id

    def records_for(uid: str) -> list[MatchRecordOut]:
        recs = (
            db.query(Record)
            .filter(Record.match_session_id == session_id, Record.user_id == uid)
            .order_by(Record.created_at)
            .all()
        )
        out: list[MatchRecordOut] = []
        for rec in recs:
            clips = (
                db.query(Clip)
                .filter(Clip.record_id == rec.id, Clip.status == "active")
                .order_by(Clip.order)
                .all()
            )
            out.append(
                MatchRecordOut(
                    record_id=rec.id,
                    walked_at=rec.walked_at,
                    clips=[
                        ClipOut(
                            id=c.id,
                            stream_url=f"/api/clips/{c.id}/stream",
                            duration_ms=c.duration_ms,
                            order=c.order,
                            mission_id=c.mission_id,
                            status=c.status,
                        )
                        for c in clips
                    ],
                )
            )
        return out

    return MatchSessionRecordsRes(mine=records_for(user.id), partner=records_for(partner_id))


@router.get("/match-sessions/{session_id}/progress")
def get_session_progress(
    session_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """매칭 산책 '중' 양측이 어떤 미션을 촬영했는지(실시간). Record는 산책 종료 시에만
    생기므로, 그 전에는 업로드된 Clip(record_id 무관)으로 진행현황을 본다.
    이 세션 시작 이후 mission_id가 있는 active 클립의 mission_id 집합을 user별로 반환."""
    session = db.get(MatchSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    if user.id not in (session.user_a_id, session.user_b_id):
        raise HTTPException(status_code=403, detail="not a participant")
    partner_id = session.user_b_id if user.id == session.user_a_id else session.user_a_id

    def missions_for(uid: str) -> list[str]:
        rows = (
            db.query(Clip.mission_id)
            .filter(
                Clip.user_id == uid,
                Clip.status == "active",
                Clip.mission_id.isnot(None),
                Clip.created_at >= session.started_at,
            )
            .all()
        )
        # 중복 제거(같은 미션 여러 컷 가능)하되 순서 무관 — set으로
        return sorted({r[0] for r in rows})

    return {"mine": missions_for(user.id), "partner": missions_for(partner_id)}


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
