"""SQLAlchemy ORM models (02_data_model.md).

All PKs are String UUID hex. Times are UTC datetimes. Arrays are stored as
JSON strings (Text). PostGIS geography is replaced by lat/lng FLOAT columns +
app-level Haversine.
"""
from __future__ import annotations

import uuid
from datetime import datetime, date

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def gen_uuid() -> str:
    return uuid.uuid4().hex


def utcnow() -> datetime:
    return datetime.utcnow()


# ---------------------------------------------------------------------------
# Common / S1
# ---------------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    nickname: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    profile_image_url: Mapped[str | None] = mapped_column(String, nullable=True)
    auth_token: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    is_mock: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Pet(Base):
    __tablename__ = "pets"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    photo_url: Mapped[str | None] = mapped_column(String, nullable=True)
    breed: Mapped[str | None] = mapped_column(String, nullable=True)
    age_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gender: Mapped[str | None] = mapped_column(String, nullable=True)
    size: Mapped[str | None] = mapped_column(String, nullable=True)
    is_neutered: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    personality_tags: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    sociality: Mapped[int | None] = mapped_column(Integer, nullable=True)
    activity_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    walk_style: Mapped[str | None] = mapped_column(String, nullable=True)
    preferred_partner_size: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    caution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class WalkSession(Base):
    __tablename__ = "walk_sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    pet_id: Mapped[str] = mapped_column(ForeignKey("pets.id"), nullable=False)
    status: Mapped[str] = mapped_column(String, default="active", index=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_location_visible: Mapped[bool] = mapped_column(Boolean, default=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class MatchRequest(Base):
    __tablename__ = "match_requests"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    requester_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    receiver_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    requester_walk_session_id: Mapped[str | None] = mapped_column(
        ForeignKey("walk_sessions.id"), nullable=True
    )
    receiver_walk_session_id: Mapped[str | None] = mapped_column(
        ForeignKey("walk_sessions.id"), nullable=True
    )
    pet_a_id: Mapped[str | None] = mapped_column(ForeignKey("pets.id"), nullable=True)
    pet_b_id: Mapped[str | None] = mapped_column(ForeignKey("pets.id"), nullable=True)
    status: Mapped[str] = mapped_column(String, default="pending", index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class MatchSession(Base):
    __tablename__ = "match_sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    match_request_id: Mapped[str] = mapped_column(ForeignKey("match_requests.id"), nullable=False)
    user_a_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    user_b_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    pet_a_id: Mapped[str | None] = mapped_column(ForeignKey("pets.id"), nullable=True)
    pet_b_id: Mapped[str | None] = mapped_column(ForeignKey("pets.id"), nullable=True)
    status: Mapped[str] = mapped_column(String, default="active", index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class MatchLog(Base):
    __tablename__ = "match_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    match_session_id: Mapped[str] = mapped_column(ForeignKey("match_sessions.id"), nullable=False)
    user_a_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    user_b_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    pet_a_id: Mapped[str | None] = mapped_column(ForeignKey("pets.id"), nullable=True)
    pet_b_id: Mapped[str | None] = mapped_column(ForeignKey("pets.id"), nullable=True)
    walked_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    distance_meters: Mapped[int | None] = mapped_column(Integer, nullable=True)
    photo_urls: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    feedback_a: Mapped[str | None] = mapped_column(String, nullable=True)
    feedback_b: Mapped[str | None] = mapped_column(String, nullable=True)
    meet_count: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


# ---------------------------------------------------------------------------
# S3 — records / clips
# ---------------------------------------------------------------------------
class Record(Base):
    __tablename__ = "records"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    walk_session_id: Mapped[str | None] = mapped_column(ForeignKey("walk_sessions.id"), nullable=True)
    match_session_id: Mapped[str | None] = mapped_column(ForeignKey("match_sessions.id"), nullable=True)
    daily_quest_id: Mapped[str | None] = mapped_column(ForeignKey("daily_quests.id"), nullable=True)
    visibility: Mapped[str] = mapped_column(String, default="diary")
    room_id: Mapped[str | None] = mapped_column(ForeignKey("rooms.id"), nullable=True)
    walked_at: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    distance_meters: Mapped[int | None] = mapped_column(Integer, nullable=True)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    decoration_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Clip(Base):
    __tablename__ = "clips"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    record_id: Mapped[str | None] = mapped_column(ForeignKey("records.id"), nullable=True, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    mission_id: Mapped[str | None] = mapped_column(ForeignKey("quest_missions.id"), nullable=True)
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    order: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


# ---------------------------------------------------------------------------
# S3 — rooms / reactions
# ---------------------------------------------------------------------------
class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String, nullable=False)
    mode: Mapped[str] = mapped_column(String, default="walk_friend")
    join_code: Mapped[str] = mapped_column(String, unique=True, index=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    max_members: Mapped[int] = mapped_column(Integer, default=5)
    status: Mapped[str] = mapped_column(String, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class RoomMember(Base):
    __tablename__ = "room_members"
    __table_args__ = (UniqueConstraint("room_id", "user_id", name="uq_room_user"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    room_id: Mapped[str] = mapped_column(ForeignKey("rooms.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String, default="joined")
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Reaction(Base):
    __tablename__ = "reactions"
    __table_args__ = (
        UniqueConstraint("target_type", "target_id", "user_id", "emoji", name="uq_reaction"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    target_type: Mapped[str] = mapped_column(String, nullable=False)
    target_id: Mapped[str] = mapped_column(String, nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    emoji: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


# ---------------------------------------------------------------------------
# S3 — quests
# ---------------------------------------------------------------------------
class QuestTemplate(Base):
    __tablename__ = "quest_templates"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    mode: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class QuestMission(Base):
    __tablename__ = "quest_missions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    quest_template_id: Mapped[str] = mapped_column(ForeignKey("quest_templates.id"), nullable=False)
    order: Mapped[int] = mapped_column(Integer, default=0)
    title: Mapped[str] = mapped_column(String, nullable=False)
    hint: Mapped[str | None] = mapped_column(Text, nullable=True)


class DailyQuest(Base):
    __tablename__ = "daily_quests"
    __table_args__ = (
        UniqueConstraint("scope", "scope_id", "quest_date", name="uq_daily_quest"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    scope: Mapped[str] = mapped_column(String, nullable=False)
    scope_id: Mapped[str] = mapped_column(String, nullable=False)
    quest_template_id: Mapped[str] = mapped_column(ForeignKey("quest_templates.id"), nullable=False)
    quest_date: Mapped[date] = mapped_column(Date, nullable=False)
    locked: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


# ---------------------------------------------------------------------------
# F-09 / common
# ---------------------------------------------------------------------------
class Block(Base):
    __tablename__ = "blocks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    blocker_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    blocked_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    reporter_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    reported_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class UserAchievement(Base):
    """Unlocked badges (F-achievements). Definitions live in code
    (services/achievements.py CATALOG); this table only records *when* a
    given user crossed a threshold, so the unlock moment can be celebrated."""

    __tablename__ = "user_achievements"
    __table_args__ = (
        UniqueConstraint("user_id", "code", name="uq_user_achievement"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String, nullable=False, index=True)
    progress_value: Mapped[int] = mapped_column(Integer, default=0)
    unlocked_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class LeagueStanding(Base):
    """A user's *current* league tier (persistent across weeks; moved by the
    weekly rollover). One row per user."""

    __tablename__ = "league_standings"
    __table_args__ = (UniqueConstraint("user_id", name="uq_league_standing_user"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    tier: Mapped[str] = mapped_column(String, default="bronze", index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class LeaguePoint(Base):
    """Append-only weekly points ledger. Weekly score = SUM(points) for the
    user in the current `week_key` (ISO year-week, e.g. 2026-W25)."""

    __tablename__ = "league_points"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    week_key: Mapped[str] = mapped_column(String, nullable=False, index=True)
    points: Mapped[int] = mapped_column(Integer, default=0)
    reason: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class LeagueState(Base):
    """Singleton bookkeeping: the last week_key the rollover processed, so
    auto-rollover stays idempotent without a scheduler."""

    __tablename__ = "league_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    last_rollover_week: Mapped[str | None] = mapped_column(String, nullable=True)


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    type: Mapped[str] = mapped_column(String, nullable=False)
    payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
