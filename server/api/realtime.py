"""Realtime (SSE) — 서버 푸시로 nearby 강아지를 스트리밍(클라이언트 폴링 대체).

EventSource 는 헤더를 못 실으므로 ?token= 으로 인증한다. 2초마다 내 활성 세션 위치 기준
nearby 를 계산해 push. 동일 출처 PoC 규모(소수 동시접속)를 가정한 단순 구현.
"""
from __future__ import annotations

import json
import time
from datetime import timedelta

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from ..database import SessionLocal
from ..models import User, WalkSession, utcnow
from .nearby import FRESH_SECONDS, compute_nearby

router = APIRouter(tags=["realtime"])

PUSH_INTERVAL = 2.0


def _my_loc(db, user):
    cutoff = utcnow() - timedelta(seconds=FRESH_SECONDS)
    ws = (
        db.query(WalkSession)
        .filter(
            WalkSession.user_id == user.id,
            WalkSession.status == "active",
            WalkSession.lat.isnot(None),
            WalkSession.location_updated_at.isnot(None),
            WalkSession.location_updated_at >= cutoff,
        )
        .order_by(WalkSession.location_updated_at.desc())
        .first()
    )
    return (ws.lat, ws.lng) if ws else (None, None)


@router.get("/stream")
def stream(token: str = Query(...), radius_meters: float = Query(1000)):
    def gen():
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.auth_token == token).first()
            if user is None:
                yield "event: error\ndata: unauthorized\n\n"
                return
            while True:
                db.expire_all()  # 매 틱 최신 상태로 다시 읽기
                lat, lng = _my_loc(db, user)
                if lat is not None:
                    dogs = compute_nearby(db, user, lat, lng, radius_meters)
                    payload = {"dogs": [d.model_dump(mode="json") for d in dogs]}
                else:
                    payload = {"dogs": []}
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                time.sleep(PUSH_INTERVAL)
        except (GeneratorExit, BrokenPipeError):
            pass
        finally:
            db.close()

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )
