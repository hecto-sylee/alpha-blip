"""Achievements (badges) domain logic.

Five badge families, all derived from data the app already records:

| family          | progress source                                              |
|-----------------|--------------------------------------------------------------|
| `friend`        | highest `MatchLog.meet_count` with any single partner        |
| `streak`        | current run of consecutive days with a record (walked_at)    |
| `quest`         | count of records that certified a daily quest                |
| `perfect_month` | number of calendar months walked *every* day (만책)          |
| `distance`      | cumulative `Record.distance_meters` (recorded, not GPS path) |

Definitions are kept in code (`CATALOG`); the DB (`UserAchievement`) only
stores the unlock moment so it can be celebrated exactly once.
"""
from __future__ import annotations

import calendar
from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models import MatchLog, Record, UserAchievement, utcnow

# --- Catalog -----------------------------------------------------------------
# Each badge: code, family, threshold, name (귀여운 이름), emoji, description.
# `threshold` is compared against the family's computed progress value.
CATALOG: list[dict] = [
    # 산책 기록 횟수 (입문 → 누적) — 첫 산책이 온보딩 첫 보상
    {"code": "walk_1",   "family": "walk", "threshold": 1,   "name": "첫 산책",     "emoji": "👣", "desc": "첫 산책을 기록했어요!"},
    {"code": "walk_10",  "family": "walk", "threshold": 10,  "name": "산책 10번",   "emoji": "🐾", "desc": "산책을 10번 기록."},
    {"code": "walk_50",  "family": "walk", "threshold": 50,  "name": "산책 50번",   "emoji": "🥾", "desc": "산책을 50번 기록."},
    {"code": "walk_100", "family": "walk", "threshold": 100, "name": "백 번의 산책", "emoji": "🎽", "desc": "산책을 100번 기록!"},

    # 동일한 친구와 N회 같이 산책 (관계 마일스톤) — MatchLog.meet_count 최댓값
    {"code": "friend_1",   "family": "friend", "threshold": 1,   "name": "초면에 반가워요 멍", "emoji": "🐶", "desc": "산책 친구와 처음으로 만났어요."},
    {"code": "friend_2",   "family": "friend", "threshold": 2,   "name": "조심스러운 친구 사이", "emoji": "🐕", "desc": "같은 친구와 두 번째 산책."},
    {"code": "friend_5",   "family": "friend", "threshold": 5,   "name": "마음을 여는 중",     "emoji": "🐾", "desc": "한 친구와 5번 만났어요."},
    {"code": "friend_10",  "family": "friend", "threshold": 10,  "name": "이제는 베프다 멍",   "emoji": "💛", "desc": "한 친구와 10번 산책!"},
    {"code": "friend_20",  "family": "friend", "threshold": 20,  "name": "둘도 없는 단짝",     "emoji": "🤝", "desc": "한 친구와 20번 산책."},
    {"code": "friend_30",  "family": "friend", "threshold": 30,  "name": "영혼의 단짝",        "emoji": "✨", "desc": "한 친구와 30번 산책."},
    {"code": "friend_50",  "family": "friend", "threshold": 50,  "name": "평생 산책 메이트",   "emoji": "🏅", "desc": "한 친구와 50번 산책."},
    {"code": "friend_100", "family": "friend", "threshold": 100, "name": "천생연분 멍",        "emoji": "💞", "desc": "한 친구와 100번 산책!"},

    # 연속 산책 일수 (streak)
    {"code": "streak_3",   "family": "streak", "threshold": 3,   "name": "작심삼일 통과 멍",   "emoji": "🔥", "desc": "3일 연속 산책."},
    {"code": "streak_7",   "family": "streak", "threshold": 7,   "name": "일주일 개근 멍",     "emoji": "📅", "desc": "7일 연속 산책."},
    {"code": "streak_14",  "family": "streak", "threshold": 14,  "name": "2주 산책러",         "emoji": "🚶", "desc": "14일 연속 산책."},
    {"code": "streak_30",  "family": "streak", "threshold": 30,  "name": "한 달 산책 마스터",  "emoji": "🏆", "desc": "30일 연속 산책."},
    {"code": "streak_100", "family": "streak", "threshold": 100, "name": "백일의 약속",        "emoji": "💯", "desc": "100일 연속 산책!"},

    # 퀘스트 로그 인증 횟수
    {"code": "quest_1",    "family": "quest",  "threshold": 1,   "name": "첫 퀘스트 인증",     "emoji": "🎯", "desc": "퀘스트를 처음 인증했어요."},
    {"code": "quest_10",   "family": "quest",  "threshold": 10,  "name": "퀘스트 수집가",      "emoji": "📸", "desc": "퀘스트 10회 인증."},
    {"code": "quest_30",   "family": "quest",  "threshold": 30,  "name": "퀘스트 마니아",      "emoji": "🎞️", "desc": "퀘스트 30회 인증."},
    {"code": "quest_50",   "family": "quest",  "threshold": 50,  "name": "퀘스트 장인",        "emoji": "🛠️", "desc": "퀘스트 50회 인증."},
    {"code": "quest_100",  "family": "quest",  "threshold": 100, "name": "퀘스트 레전드",      "emoji": "👑", "desc": "퀘스트 100회 인증!"},

    # 월간 만책 (그 달의 모든 날에 산책)
    {"code": "perfect_1",  "family": "perfect_month", "threshold": 1,  "name": "이달의 만책 멍",  "emoji": "🗓️", "desc": "한 달 내내 하루도 빠짐없이 산책!"},
    {"code": "perfect_3",  "family": "perfect_month", "threshold": 3,  "name": "만책 3관왕",      "emoji": "🥉", "desc": "만책을 3번 달성."},
    {"code": "perfect_6",  "family": "perfect_month", "threshold": 6,  "name": "반년 만책",       "emoji": "🥈", "desc": "만책을 6번 달성."},
    {"code": "perfect_12", "family": "perfect_month", "threshold": 12, "name": "만책 개근왕",     "emoji": "🥇", "desc": "만책을 12번 달성!"},

    # 누적 거리 (기록 거리 합산, meters)
    {"code": "dist_5k",    "family": "distance", "threshold": 5_000,   "name": "동네 한 바퀴",     "emoji": "🐾", "desc": "누적 5km 산책."},
    {"code": "dist_10k",   "family": "distance", "threshold": 10_000,  "name": "산책 워밍업",      "emoji": "🚶", "desc": "누적 10km 산책."},
    {"code": "dist_marathon", "family": "distance", "threshold": 42_195, "name": "강아지 마라토너", "emoji": "🏃", "desc": "누적 42.195km, 풀코스 완주!"},
    {"code": "dist_100k",  "family": "distance", "threshold": 100_000, "name": "백 킬로미터 멍",   "emoji": "🎖️", "desc": "누적 100km 산책."},
    {"code": "dist_500k",  "family": "distance", "threshold": 500_000, "name": "대장정 멍",        "emoji": "🗺️", "desc": "누적 500km 산책!"},
]

CATALOG_BY_CODE = {a["code"]: a for a in CATALOG}

FAMILY_LABELS = {
    "walk": "산책",
    "friend": "산책 친구",
    "streak": "연속 산책",
    "quest": "퀘스트",
    "perfect_month": "만책",
    "distance": "누적 거리",
}
# Stable display order for families.
FAMILY_ORDER = ["walk", "friend", "streak", "quest", "perfect_month", "distance"]


# --- Progress computation ----------------------------------------------------
def _walked_dates(db: Session, user_id: str) -> list[date]:
    rows = (
        db.query(Record.walked_at)
        .filter(Record.user_id == user_id, Record.walked_at.isnot(None))
        .distinct()
        .all()
    )
    return sorted({r[0] for r in rows})


def _current_streak(walked: set[date], today: date) -> int:
    if not walked:
        return 0
    # 오늘 기록이 없으면 어제부터 카운트 (diary.js computeStreak와 동일 규칙)
    cursor = today if today in walked else today - timedelta(days=1)
    streak = 0
    while cursor in walked:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def _perfect_months(walked: list[date]) -> int:
    by_month: dict[tuple[int, int], set[int]] = {}
    for d in walked:
        by_month.setdefault((d.year, d.month), set()).add(d.day)
    count = 0
    for (year, month), days in by_month.items():
        if len(days) == calendar.monthrange(year, month)[1]:
            count += 1
    return count


def compute_progress(db: Session, user_id: str, today: date | None = None) -> dict[str, int]:
    """Return the current progress value for each badge family."""
    today = today or utcnow().date()

    max_meet = (
        db.query(func.max(MatchLog.meet_count))
        .filter((MatchLog.user_a_id == user_id) | (MatchLog.user_b_id == user_id))
        .scalar()
    ) or 0

    walk_count = (
        db.query(func.count(Record.id)).filter(Record.user_id == user_id).scalar()
    ) or 0

    quest_certs = (
        db.query(func.count(Record.id))
        .filter(Record.user_id == user_id, Record.daily_quest_id.isnot(None))
        .scalar()
    ) or 0

    total_distance = (
        db.query(func.coalesce(func.sum(Record.distance_meters), 0))
        .filter(Record.user_id == user_id)
        .scalar()
    ) or 0

    walked = _walked_dates(db, user_id)
    return {
        "walk": int(walk_count),
        "friend": int(max_meet),
        "streak": _current_streak(set(walked), today),
        "quest": int(quest_certs),
        "perfect_month": _perfect_months(walked),
        "distance": int(total_distance),
    }


# --- Evaluate (unlock) + listing --------------------------------------------
def evaluate(db: Session, user_id: str, today: date | None = None) -> list[dict]:
    """Unlock any newly-earned badges. Adds rows + flushes (caller commits).

    Returns the freshly-unlocked badge dicts (code/name/emoji/family) so the
    caller can surface a celebration. Idempotent: already-unlocked badges are
    never re-emitted.
    """
    progress = compute_progress(db, user_id, today)
    owned = {
        row[0]
        for row in db.query(UserAchievement.code).filter(UserAchievement.user_id == user_id).all()
    }
    newly: list[dict] = []
    for badge in CATALOG:
        if badge["code"] in owned:
            continue
        if progress.get(badge["family"], 0) >= badge["threshold"]:
            db.add(
                UserAchievement(
                    user_id=user_id,
                    code=badge["code"],
                    progress_value=progress[badge["family"]],
                )
            )
            newly.append(
                {"code": badge["code"], "name": badge["name"], "emoji": badge["emoji"], "family": badge["family"]}
            )
    if newly:
        db.flush()
    return newly


def list_for_user(db: Session, user_id: str, today: date | None = None) -> dict:
    """Full badge grid for the My screen: progress summary + per-badge state."""
    progress = compute_progress(db, user_id, today)
    unlocked_at = {
        row.code: row.unlocked_at
        for row in db.query(UserAchievement).filter(UserAchievement.user_id == user_id).all()
    }
    items = []
    for badge in CATALOG:
        value = progress.get(badge["family"], 0)
        ua = unlocked_at.get(badge["code"])
        items.append(
            {
                "code": badge["code"],
                "family": badge["family"],
                "family_label": FAMILY_LABELS.get(badge["family"], badge["family"]),
                "name": badge["name"],
                "emoji": badge["emoji"],
                "description": badge["desc"],
                "threshold": badge["threshold"],
                "value": value,
                "unlocked": ua is not None,
                "unlocked_at": ua,
            }
        )
    summary = {
        "unlocked_count": sum(1 for it in items if it["unlocked"]),
        "total_count": len(items),
        "progress": progress,
    }
    return {"summary": summary, "achievements": items}
