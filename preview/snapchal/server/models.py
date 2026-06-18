from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, Float, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from database import Base


def gen_id():
    return str(uuid.uuid4())


class Room(Base):
    __tablename__ = "rooms"

    id = Column(String, primary_key=True, default=gen_id)
    name = Column(String, nullable=False)
    mode = Column(String, nullable=False)  # friend | couple
    join_code = Column(String, unique=True, nullable=False)
    invite_url = Column(String, nullable=False)
    max_participants = Column(Integer, default=5)
    status = Column(String, default="active")  # active | deleted
    created_at = Column(DateTime, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

    participants = relationship("Participant", back_populates="room")
    daily_logs = relationship("DailyLog", back_populates="room")
    analytics_events = relationship("AnalyticsEvent", back_populates="room")


class Participant(Base):
    __tablename__ = "participants"

    id = Column(String, primary_key=True, default=gen_id)
    room_id = Column(String, ForeignKey("rooms.id"), nullable=False)
    device_id = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    joined_at = Column(DateTime, default=datetime.utcnow)
    left_at = Column(DateTime, nullable=True)
    status = Column(String, default="active")  # active | left

    room = relationship("Room", back_populates="participants")
    video_clips = relationship("VideoClip", back_populates="participant")
    reactions = relationship("Reaction", back_populates="participant")


class DailyLog(Base):
    __tablename__ = "daily_logs"

    id = Column(String, primary_key=True, default=gen_id)
    room_id = Column(String, ForeignKey("rooms.id"), nullable=False)
    date = Column(String, nullable=False)  # YYYY-MM-DD
    daily_quest_id = Column(String, ForeignKey("daily_quests.id"), nullable=True)
    status = Column(String, default="open")  # open | closed
    created_at = Column(DateTime, default=datetime.utcnow)

    room = relationship("Room", back_populates="daily_logs")
    daily_quest = relationship("DailyQuest", back_populates="daily_log", foreign_keys=[daily_quest_id])
    video_clips = relationship("VideoClip", back_populates="daily_log")


class QuestTemplate(Base):
    __tablename__ = "quest_templates"

    id = Column(String, primary_key=True, default=gen_id)
    quest_id = Column(String, unique=True, nullable=False)  # FQ-001, CQ-001 etc.
    mode = Column(String, nullable=False)  # friend | couple
    title = Column(String, nullable=False)
    short_description = Column(String, nullable=False)
    full_description = Column(String, nullable=False)
    tone = Column(String, nullable=True)
    difficulty = Column(String, default="easy")
    fallback = Column(Boolean, default=False)
    tags = Column(Text, nullable=True)  # JSON string
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    missions = relationship("QuestMissionTemplate", back_populates="template")


class QuestMissionTemplate(Base):
    __tablename__ = "quest_mission_templates"

    id = Column(String, primary_key=True, default=gen_id)
    template_id = Column(String, ForeignKey("quest_templates.id"), nullable=False)
    hour_slot = Column(String, nullable=False)  # "06:00", "07:00" etc.
    mission_title = Column(String, nullable=False)
    instruction = Column(String, nullable=False)
    example = Column(String, nullable=True)
    order = Column(Integer, nullable=False)

    template = relationship("QuestTemplate", back_populates="missions")


class DailyQuest(Base):
    __tablename__ = "daily_quests"

    id = Column(String, primary_key=True, default=gen_id)
    room_id = Column(String, ForeignKey("rooms.id"), nullable=False)
    date = Column(String, nullable=False)  # YYYY-MM-DD
    template_id = Column(String, ForeignKey("quest_templates.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    selected_by_participant_id = Column(String, ForeignKey("participants.id"), nullable=False)
    selected_at = Column(DateTime, default=datetime.utcnow)
    source = Column(String, default="pre_generated")
    locked = Column(Boolean, default=True)

    template = relationship("QuestTemplate")
    selected_by = relationship("Participant")
    daily_log = relationship("DailyLog", back_populates="daily_quest", foreign_keys="DailyLog.daily_quest_id")


class VideoClip(Base):
    __tablename__ = "video_clips"

    id = Column(String, primary_key=True, default=gen_id)
    room_id = Column(String, ForeignKey("rooms.id"), nullable=False)
    daily_log_id = Column(String, ForeignKey("daily_logs.id"), nullable=False)
    participant_id = Column(String, ForeignKey("participants.id"), nullable=False)
    daily_quest_id = Column(String, ForeignKey("daily_quests.id"), nullable=True)
    date = Column(String, nullable=False)  # YYYY-MM-DD
    hour_slot = Column(String, nullable=False)  # "06:00", "07:00" etc.
    file_path = Column(String, nullable=True)
    duration_sec = Column(Integer, default=2)
    upload_status = Column(String, default="uploading")  # uploading | uploaded | failed
    visible_in_shared_log = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    uploaded_at = Column(DateTime, nullable=True)
    hidden_at = Column(DateTime, nullable=True)

    participant = relationship("Participant", back_populates="video_clips")
    daily_log = relationship("DailyLog", back_populates="video_clips")
    reactions = relationship("Reaction", back_populates="video_clip")


class Reaction(Base):
    __tablename__ = "reactions"

    id = Column(String, primary_key=True, default=gen_id)
    video_clip_id = Column(String, ForeignKey("video_clips.id"), nullable=False)
    participant_id = Column(String, ForeignKey("participants.id"), nullable=False)
    emoji = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    video_clip = relationship("VideoClip", back_populates="reactions")
    participant = relationship("Participant", back_populates="reactions")


class ShareRecord(Base):
    __tablename__ = "share_records"

    id = Column(String, primary_key=True, default=gen_id)
    room_id = Column(String, ForeignKey("rooms.id"), nullable=False)
    daily_log_id = Column(String, ForeignKey("daily_logs.id"), nullable=True)
    participant_id = Column(String, ForeignKey("participants.id"), nullable=False)
    action_type = Column(String, nullable=False)  # save | share
    created_at = Column(DateTime, default=datetime.utcnow)


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"

    id = Column(String, primary_key=True, default=gen_id)
    event_name = Column(String, nullable=False)
    room_id = Column(String, ForeignKey("rooms.id"), nullable=True)
    participant_id = Column(String, nullable=True)
    device_id = Column(String, nullable=True)
    properties = Column(Text, nullable=True)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)

    room = relationship("Room", back_populates="analytics_events")
