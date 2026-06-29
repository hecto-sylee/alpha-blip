"""포인트(소비 재화) 적립. 리그 점수와 별개로, 상점에서 쓰는 재화.

지급 기준(명확):
  - 산책 완주(기록 1건): +PER_WALK
  - 촬영한 클립(퀘스트 순간) 1개당: +PER_CLIP
  - 매칭(함께) 산책: +MATCH_BONUS (협동 보너스)
예) 솔로 3컷 = 10 + 5*3 = 25.  매칭 3컷 = 10 + 5*3 + 20 = 45.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from ..models import User

PER_WALK = 10      # 산책 1회 완주
PER_CLIP = 5       # 클립(퀘스트 순간) 1개당
MATCH_BONUS = 20   # 함께 산책(매칭) 보너스


def award(db: Session, user: User, amount: int) -> int:
    user.points = (user.points or 0) + amount
    return amount


def award_for_record(db: Session, user: User, *, clip_count: int = 0, is_match: bool = False) -> int:
    """기록 저장 시 적립할 포인트를 계산·반영하고 적립량을 반환한다."""
    amount = PER_WALK + PER_CLIP * max(0, clip_count)
    if is_match:
        amount += MATCH_BONUS
    return award(db, user, amount)
