"""Helper to append an analytics_events row for core actions."""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from ..models import AnalyticsEvent


def log_event(db: Session, type: str, user_id: str | None = None, payload: dict | None = None) -> None:
    ev = AnalyticsEvent(
        user_id=user_id,
        type=type,
        payload_json=json.dumps(payload, ensure_ascii=False) if payload else None,
    )
    db.add(ev)
