"""포인트(소비 재화) 적립. 리그 점수와 별개로, 상점에서 쓰는 재화."""
from __future__ import annotations

from sqlalchemy.orm import Session

from ..models import User

BASE_PER_RECORD = 10     # 기록(산책) 저장 기본
QUEST_BONUS = 15         # 퀘스트 인증(daily_quest 연결) 보너스


def award(db: Session, user: User, amount: int) -> int:
    user.points = (user.points or 0) + amount
    return amount


def award_for_record(db: Session, user: User, quest_certified: bool) -> int:
    """기록 저장 시 적립할 포인트를 계산·반영하고, 적립량을 반환한다."""
    amount = BASE_PER_RECORD + (QUEST_BONUS if quest_certified else 0)
    return award(db, user, amount)
