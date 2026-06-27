"""Pydantic v2 request/response DTOs (M0-M2 focus)."""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
class GuestSignupReq(BaseModel):
    nickname: str


class GuestSignupRes(BaseModel):
    user_id: str
    auth_token: str


class LoginReq(BaseModel):
    login_id: str
    nickname: str | None = None


class LoginRes(BaseModel):
    user_id: str
    auth_token: str
    nickname: str
    is_new: bool = False


class KakaoLoginReq(BaseModel):
    code: str
    redirect_uri: str | None = None


class KakaoLoginRes(BaseModel):
    user_id: str
    auth_token: str
    nickname: str
    is_new: bool = False


class KakaoUrlRes(BaseModel):
    enabled: bool = False
    authorize_url: str | None = None


class PetSummary(BaseModel):
    id: str
    name: str
    breed: str | None = None
    photo_url: str | None = None
    size: str | None = None
    personality_tags: list[str] = []
    appearance: dict | None = None  # 픽셀 외형/커마(마커·아바타 렌더용)


class MeRes(BaseModel):
    id: str
    nickname: str
    profile_image_url: str | None = None
    points: int = 0
    pets: list[PetSummary] = []


# ---------------------------------------------------------------------------
# Pets
# ---------------------------------------------------------------------------
class PetCreateReq(BaseModel):
    name: str
    photo_url: str | None = None
    breed: str | None = None
    age_months: int | None = None
    gender: str | None = None
    size: str | None = None
    is_neutered: bool | None = None
    personality_tags: list[str] | None = None
    sociality: int | None = None
    activity_level: int | None = None
    walk_style: str | None = None
    preferred_partner_size: list[str] | None = None
    caution_notes: str | None = None
    appearance: dict | None = None  # 픽셀 외형/커마


class PetUpdateReq(BaseModel):
    name: str | None = None
    photo_url: str | None = None
    breed: str | None = None
    age_months: int | None = None
    gender: str | None = None
    size: str | None = None
    is_neutered: bool | None = None
    personality_tags: list[str] | None = None
    sociality: int | None = None
    activity_level: int | None = None
    walk_style: str | None = None
    preferred_partner_size: list[str] | None = None
    caution_notes: str | None = None
    appearance: dict | None = None  # 픽셀 외형/커마


class PetCreateRes(BaseModel):
    pet_id: str


class PetRes(BaseModel):
    id: str
    name: str
    photo_url: str | None = None
    breed: str | None = None
    age_months: int | None = None
    gender: str | None = None
    size: str | None = None
    is_neutered: bool | None = None
    personality_tags: list[str] = []
    sociality: int | None = None
    activity_level: int | None = None
    walk_style: str | None = None
    preferred_partner_size: list[str] = []
    caution_notes: str | None = None
    appearance: dict | None = None  # 픽셀 외형/커마


class PetListRes(BaseModel):
    pets: list[PetRes] = []


# ---------------------------------------------------------------------------
# Walks
# ---------------------------------------------------------------------------
class WalkStartReq(BaseModel):
    pet_id: str
    latitude: float | None = None
    longitude: float | None = None


class WalkStartRes(BaseModel):
    walk_session_id: str
    started_at: datetime


class LocationReq(BaseModel):
    latitude: float
    longitude: float


class WalkEndReq(BaseModel):
    ended_at: datetime | None = None
    duration_minutes: int | None = None


# ---------------------------------------------------------------------------
# Nearby
# ---------------------------------------------------------------------------
class ApproxLocation(BaseModel):
    latitude: float
    longitude: float


class NearbyDog(BaseModel):
    walk_session_id: str
    pet: PetRes
    distance_meters: int
    approximate_location: ApproxLocation


class NearbyRes(BaseModel):
    dogs: list[NearbyDog]


# ---------------------------------------------------------------------------
# Demo mode
# ---------------------------------------------------------------------------
class DemoSetupReq(BaseModel):
    latitude: float | None = None
    longitude: float | None = None


class DemoLocation(BaseModel):
    latitude: float
    longitude: float
    label: str


class DemoSetupRes(BaseModel):
    mock_user_id: str
    mock_pet: PetRes
    mock_walk_session_id: str
    room_id: str
    room_join_code: str
    location: DemoLocation
    mock_location: DemoLocation


# ---------------------------------------------------------------------------
# Matches
# ---------------------------------------------------------------------------
class MatchRequestReq(BaseModel):
    receiver_walk_session_id: str


class MatchRequestRes(BaseModel):
    match_request_id: str
    expires_at: datetime | None = None


class IncomingRequest(BaseModel):
    id: str
    requester: dict
    pet: dict | None = None
    status: str
    expires_at: datetime | None = None
    created_at: datetime


class IncomingRes(BaseModel):
    requests: list[IncomingRequest]


class AcceptRes(BaseModel):
    match_session_id: str


class MatchSessionRes(BaseModel):
    id: str
    status: str
    partner: dict
    started_at: datetime
    a_met: bool = False
    b_met: bool = False
    both_met: bool = False
    i_met: bool = False  # 요청자(나) 기준 met 여부


class MatchEndReq(BaseModel):
    duration_minutes: int | None = None
    distance_meters: int | None = None


class UnlockedAchievement(BaseModel):
    code: str
    name: str
    emoji: str
    family: str


class MatchEndRes(BaseModel):
    match_log_id: str
    unlocked: list[UnlockedAchievement] = []


# ---------------------------------------------------------------------------
# Records (F-10)
# ---------------------------------------------------------------------------
class RecordCreateReq(BaseModel):
    walk_session_id: str | None = None
    match_session_id: str | None = None
    daily_quest_id: str | None = None
    visibility: str = "diary"
    room_id: str | None = None
    walked_at: date | None = None
    duration_minutes: int | None = None
    distance_meters: int | None = None
    text: str | None = None
    decoration_json: str | None = None
    clip_ids: list[str] = []


class RecordCreateRes(BaseModel):
    record_id: str
    unlocked: list[UnlockedAchievement] = []
    points_awarded: int = 0
    points: int = 0


# ---------------------------------------------------------------------------
# Shop / points
# ---------------------------------------------------------------------------
class ShopBuyReq(BaseModel):
    item_key: str


class ShopItemRes(BaseModel):
    key: str
    name: str
    slot: str
    cost: int
    owned: bool = False


class ShopRes(BaseModel):
    points: int = 0
    items: list[ShopItemRes] = []


# ---------------------------------------------------------------------------
# Achievements (badges)
# ---------------------------------------------------------------------------
class AchievementOut(BaseModel):
    code: str
    family: str
    family_label: str
    name: str
    emoji: str
    description: str
    threshold: int
    value: int
    unlocked: bool
    unlocked_at: datetime | None = None


class AchievementSummary(BaseModel):
    unlocked_count: int
    total_count: int
    progress: dict[str, int]


class AchievementListRes(BaseModel):
    summary: AchievementSummary
    achievements: list[AchievementOut]


class AchievementEvaluateRes(BaseModel):
    unlocked: list[UnlockedAchievement] = []


# ---------------------------------------------------------------------------
# Leagues (ranking)
# ---------------------------------------------------------------------------
class LeagueEntry(BaseModel):
    rank: int
    name: str
    points: int
    is_me: bool = False
    is_bot: bool = False
    zone: str  # promote | maintain | demote


class LeagueMeRes(BaseModel):
    tier: str
    tier_label: str
    tier_emoji: str
    week_key: str
    cohort_size: int
    my_rank: int
    my_points: int
    promote_rank_max: int
    demote_rank_min: int
    entries: list[LeagueEntry]


class LeagueRolloverRes(BaseModel):
    week_key: str
    promoted: int
    demoted: int
    stayed: int
    skipped: bool = False
    your_tier: str | None = None


class RecordUpdateReq(BaseModel):
    text: str | None = None
    decoration_json: str | None = None
    duration_minutes: int | None = None
    distance_meters: int | None = None
    visibility: str | None = None


class ClipOut(BaseModel):
    id: str
    stream_url: str
    duration_ms: int | None = None
    order: int = 0
    mission_id: str | None = None
    status: str = "active"


class ReactionAgg(BaseModel):
    emoji: str
    count: int


class RecordOut(BaseModel):
    id: str
    user_id: str
    visibility: str
    room_id: str | None = None
    match_session_id: str | None = None  # W5: 매칭 산책 여부 판단용(기록 탭 상대영상)
    walked_at: date | None = None
    duration_minutes: int | None = None
    distance_meters: int | None = None
    text: str | None = None
    decoration_json: str | None = None
    daily_quest_id: str | None = None
    clips: list[ClipOut] = []
    reactions: list[ReactionAgg] = []
    merged_ready: bool = False  # 합성 영상 다운로드 가능 여부
    created_at: datetime


class RecordListRes(BaseModel):
    records: list[RecordOut]


# ---------------------------------------------------------------------------
# Clips (F-10)
# ---------------------------------------------------------------------------
class ClipUploadRes(BaseModel):
    clip_id: str
    file_path: str
    stream_url: str


# ---------------------------------------------------------------------------
# Quests (F-12)
# ---------------------------------------------------------------------------
class MissionOut(BaseModel):
    id: str
    order: int
    title: str
    hint: str | None = None


class QuestCandidate(BaseModel):
    quest_template_id: str
    title: str
    description: str | None = None
    missions: list[MissionOut] = []


class CandidatesRes(BaseModel):
    locked: bool
    candidates: list[QuestCandidate]


class QuestSelectReq(BaseModel):
    scope: str
    scope_id: str
    quest_template_id: str
    quest_date: date


class QuestSelectRes(BaseModel):
    daily_quest_id: str
    locked: bool


# ---------------------------------------------------------------------------
# Rooms (F-11)
# ---------------------------------------------------------------------------
class RoomCreateReq(BaseModel):
    name: str
    mode: str = "walk_friend"


class RoomCreateRes(BaseModel):
    room_id: str
    join_code: str


class RoomCardOut(BaseModel):
    room_id: str
    name: str
    mode: str
    join_code: str
    member_count: int


# ---------------------------------------------------------------------------
# Reactions (F-11)
# ---------------------------------------------------------------------------
class ReactionReq(BaseModel):
    target_type: str
    target_id: str
    emoji: str


# ---------------------------------------------------------------------------
# Privacy (F-09)
# ---------------------------------------------------------------------------
class BlockReq(BaseModel):
    target_user_id: str


class ReportReq(BaseModel):
    target_user_id: str
    reason: str | None = None
    context: str | None = None


# ---------------------------------------------------------------------------
# Pet diary (W6)
# ---------------------------------------------------------------------------
class PetDiaryCreateReq(BaseModel):
    pet_id: str | None = None
    diary_date: date
    mood: str
    activity_tags: list[str] = []
    text: str | None = None


class PetDiaryUpdateReq(BaseModel):
    mood: str | None = None
    activity_tags: list[str] | None = None
    text: str | None = None


class PetDiaryCreateRes(BaseModel):
    pet_diary_id: str


class PetDiaryOut(BaseModel):
    id: str
    pet_id: str | None = None
    diary_date: date
    mood: str
    activity_tags: list[str] = []
    text: str | None = None
    created_at: datetime


class PetDiaryListRes(BaseModel):
    diaries: list[PetDiaryOut] = []


# ---------------------------------------------------------------------------
# Match session records (W5) — 매칭 양측 기록 영상 조회
# ---------------------------------------------------------------------------
class MatchRecordOut(BaseModel):
    record_id: str
    walked_at: date | None = None
    clips: list[ClipOut] = []


class MatchSessionRecordsRes(BaseModel):
    mine: list[MatchRecordOut] = []
    partner: list[MatchRecordOut] = []
