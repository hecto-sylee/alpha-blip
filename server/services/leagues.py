"""League ranking (말해보카/듀오링고풍 주간 리그).

- 점수원: 산책 기록(+10), 퀘스트 인증(+20), 연속 보너스(+min(streak,7)).
- 6단계 리그: 브론즈 < 실버 < 골드 < 플래티넘 < 다이아 < 마스터.
- 주(week_key=ISO 연-주) 단위 집계. 코호트 30명, 인원이 모자라면 AI 프로필로 채움.
- 집계(rollover): 상위 10 승급 / 중위 10 유지 / 하위 10 강등. 마스터는 승급 없음,
  브론즈는 강등 없음. 수동 엔드포인트 + 접근 시 지난 주 자동 집계(멱등).
"""
from __future__ import annotations

import hashlib
from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models import LeaguePoint, LeagueStanding, LeagueState, User, utcnow
from . import achievements as ach

TIERS = ["bronze", "silver", "gold", "platinum", "diamond", "master"]
TIER_LABELS = {
    "bronze": "브론즈", "silver": "실버", "gold": "골드",
    "platinum": "플래티넘", "diamond": "다이아", "master": "마스터",
}
TIER_EMOJI = {
    "bronze": "🥉", "silver": "🥈", "gold": "🥇",
    "platinum": "💠", "diamond": "💎", "master": "👑",
}
TIER_BASE = {"bronze": 60, "silver": 110, "gold": 180, "platinum": 260, "diamond": 360, "master": 480}

COHORT_SIZE = 30
PROMOTE = 10
DEMOTE = 10

POINTS_WALK = 10
POINTS_QUEST = 20
STREAK_BONUS_CAP = 7

_BOT_NAMES = [
    "몽이아빠", "초코맘", "바둑이집사", "뽀삐언니", "두부아빠", "감자맘", "콩이네",
    "치즈집사", "호두맘", "라떼아빠", "보리네", "구름이맘", "단추집사", "뭉치아빠",
    "나비맘", "사랑이네", "루비집사", "쿠키맘", "별이아빠", "흰둥이네", "havana맘",
    "젤리아빠", "메리집사", "복실이네", "땅콩맘", "초롱아빠", "방울이네", "또또맘",
    "havi집사", "코코아빠",
]


# --- week helpers ------------------------------------------------------------
def week_key(d: date) -> str:
    iso = d.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def prev_week_key(d: date) -> str:
    return week_key(d - timedelta(days=7))


# --- state / standing --------------------------------------------------------
def _state(db: Session) -> LeagueState:
    st = db.get(LeagueState, 1)
    if st is None:
        st = LeagueState(id=1, last_rollover_week=None)
        db.add(st)
        db.flush()
    return st


def ensure_standing(db: Session, user_id: str) -> LeagueStanding:
    st = db.query(LeagueStanding).filter(LeagueStanding.user_id == user_id).first()
    if st is None:
        st = LeagueStanding(user_id=user_id, tier="bronze")
        db.add(st)
        db.flush()
    return st


def weekly_points(db: Session, user_id: str, wk: str) -> int:
    return (
        db.query(func.coalesce(func.sum(LeaguePoint.points), 0))
        .filter(LeaguePoint.user_id == user_id, LeaguePoint.week_key == wk)
        .scalar()
    ) or 0


# --- scoring -----------------------------------------------------------------
def award_for_record(db: Session, user_id: str, *, quest_certified: bool, streak: int, when: date | None = None) -> int:
    """Award weekly league points for a saved walk record (caller commits)."""
    when = when or utcnow().date()
    pts = POINTS_WALK + (POINTS_QUEST if quest_certified else 0) + min(max(streak, 0), STREAK_BONUS_CAP)
    db.add(
        LeaguePoint(
            user_id=user_id,
            week_key=week_key(when),
            points=pts,
            reason="walk+quest" if quest_certified else "walk",
        )
    )
    ensure_standing(db, user_id)
    db.flush()
    return pts


# --- cohort assembly ---------------------------------------------------------
def _bot_points(wk: str, tier: str, i: int) -> int:
    h = int(hashlib.sha1(f"{wk}:{tier}:{i}".encode()).hexdigest(), 16)
    base = TIER_BASE[tier]
    return base // 3 + (h % base)


def _bot_name(wk: str, tier: str, i: int) -> str:
    h = int(hashlib.sha1(f"name:{wk}:{tier}:{i}".encode()).hexdigest(), 16)
    return _BOT_NAMES[h % len(_BOT_NAMES)]


def _zone(rank: int, n: int, tier: str) -> str:
    if tier != TIERS[-1] and rank <= PROMOTE:
        return "promote"
    if tier != TIERS[0] and rank > n - DEMOTE:
        return "demote"
    return "maintain"


def _build_cohort(db: Session, tier: str, wk: str, focus_user_id: str | None) -> list[dict]:
    """Active real members of (tier, week) + AI fillers up to COHORT_SIZE,
    sorted by points desc with stable tiebreak. Returns ranked entries."""
    entries: list[dict] = []
    seen = set()
    for st in db.query(LeagueStanding).filter(LeagueStanding.tier == tier).all():
        pts = weekly_points(db, st.user_id, wk)
        if pts > 0 or st.user_id == focus_user_id:
            u = db.get(User, st.user_id)
            entries.append({
                "user_id": st.user_id,
                "name": (u.nickname if u else "산책러"),
                "points": pts,
                "is_bot": False,
            })
            seen.add(st.user_id)

    fill = max(0, COHORT_SIZE - len(entries))
    for i in range(fill):
        entries.append({
            "user_id": None,
            "name": _bot_name(wk, tier, i),
            "points": _bot_points(wk, tier, i),
            "is_bot": True,
        })

    # 점수 내림차순, 동점은 이름으로 안정 정렬
    entries.sort(key=lambda e: (-e["points"], e["name"]))
    n = len(entries)
    for idx, e in enumerate(entries):
        e["rank"] = idx + 1
        e["zone"] = _zone(e["rank"], n, tier)
    return entries


# --- leaderboard (read) ------------------------------------------------------
def leaderboard(db: Session, user_id: str, today: date | None = None) -> dict:
    today = today or utcnow().date()
    ensure_standing(db, user_id)
    _maybe_auto_rollover(db, today)

    st = ensure_standing(db, user_id)
    tier = st.tier
    wk = week_key(today)
    cohort = _build_cohort(db, tier, wk, user_id)

    me = next((e for e in cohort if e.get("user_id") == user_id), None)
    n = len(cohort)
    entries = [
        {
            "rank": e["rank"],
            "name": e["name"],
            "points": e["points"],
            "is_me": e.get("user_id") == user_id,
            "is_bot": e["is_bot"],
            "zone": e["zone"],
        }
        for e in cohort
    ]
    return {
        "tier": tier,
        "tier_label": TIER_LABELS[tier],
        "tier_emoji": TIER_EMOJI[tier],
        "week_key": wk,
        "cohort_size": n,
        "my_rank": me["rank"] if me else n,
        "my_points": me["points"] if me else 0,
        "promote_rank_max": PROMOTE if tier != TIERS[-1] else 0,
        "demote_rank_min": (n - DEMOTE + 1) if tier != TIERS[0] else n + 1,
        "entries": entries,
    }


# --- rollover (write) --------------------------------------------------------
def _adjacent_tier(tier: str, direction: int) -> str:
    i = TIERS.index(tier)
    j = min(len(TIERS) - 1, max(0, i + direction))
    return TIERS[j]


def _rollover(db: Session, wk: str, *, force: bool) -> dict:
    state = _state(db)
    if not force and state.last_rollover_week == wk:
        return {"week_key": wk, "promoted": 0, "demoted": 0, "stayed": 0, "skipped": True}

    promoted = demoted = stayed = 0
    for tier in TIERS:
        cohort = _build_cohort(db, tier, wk, None)
        for e in cohort:
            if e["is_bot"] or e["user_id"] is None:
                continue
            if e["points"] <= 0:
                continue  # 그 주에 활동 없으면 이동 없음
            st = db.query(LeagueStanding).filter(LeagueStanding.user_id == e["user_id"]).first()
            if st is None:
                continue
            if e["zone"] == "promote":
                st.tier = _adjacent_tier(tier, +1)
                promoted += 1
            elif e["zone"] == "demote":
                st.tier = _adjacent_tier(tier, -1)
                demoted += 1
            else:
                stayed += 1
    state.last_rollover_week = wk
    db.flush()
    return {"week_key": wk, "promoted": promoted, "demoted": demoted, "stayed": stayed, "skipped": False}


def _maybe_auto_rollover(db: Session, today: date) -> None:
    """On access, settle the most recently completed week exactly once."""
    pw = prev_week_key(today)
    state = _state(db)
    if state.last_rollover_week == pw:
        return
    had_activity = db.query(LeaguePoint.id).filter(LeaguePoint.week_key == pw).first()
    if had_activity:
        _rollover(db, pw, force=True)


def rollover(db: Session, user_id: str | None = None, week: str | None = None, today: date | None = None) -> dict:
    """Manual trigger. Defaults to settling the *current* week so the effect is
    immediately visible (demo-friendly); same code path as auto-rollover."""
    today = today or utcnow().date()
    wk = week or week_key(today)
    result = _rollover(db, wk, force=True)
    if user_id:
        st = ensure_standing(db, user_id)
        result["your_tier"] = st.tier
    return result
