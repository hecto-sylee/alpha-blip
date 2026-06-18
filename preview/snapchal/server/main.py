import os
import uuid
import json
import random
import shutil
from datetime import datetime, date
from typing import Optional, List
from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import engine, get_db, Base
from models import (
    Room, Participant, DailyLog, QuestTemplate, QuestMissionTemplate,
    DailyQuest, VideoClip, Reaction, ShareRecord, AnalyticsEvent
)
from quest_data import QUEST_TEMPLATES

# DB 초기화
Base.metadata.create_all(bind=engine)

app = FastAPI(title="스냅챌 API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

STATIC_DIR = Path("static")


# ─── 퀘스트 데이터 초기 적재 ───────────────────────────────────────────────────

def seed_quests(db: Session):
    if db.query(QuestTemplate).count() > 0:
        return
    for qt_data in QUEST_TEMPLATES:
        missions = qt_data.pop("missions")
        tags = json.dumps(qt_data.pop("tags", []))
        qt = QuestTemplate(
            id=str(uuid.uuid4()),
            quest_id=qt_data["quest_id"],
            mode=qt_data["mode"],
            title=qt_data["title"],
            short_description=qt_data["short_description"],
            full_description=qt_data["full_description"],
            tone=qt_data.get("tone"),
            difficulty=qt_data.get("difficulty", "easy"),
            fallback=qt_data.get("fallback", False),
            tags=tags,
            enabled=True,
        )
        db.add(qt)
        db.flush()
        for m in missions:
            mission = QuestMissionTemplate(
                id=str(uuid.uuid4()),
                template_id=qt.id,
                hour_slot=m["hour_slot"],
                mission_title=m["mission_title"],
                instruction=m["instruction"],
                example=m.get("example"),
                order=m["order"],
            )
            db.add(mission)
    db.commit()


@app.on_event("startup")
async def startup():
    from database import SessionLocal
    db = SessionLocal()
    try:
        seed_quests(db)
    finally:
        db.close()


# ─── 헬퍼 ─────────────────────────────────────────────────────────────────────

def log_event(db: Session, event_name: str, room_id=None, participant_id=None, device_id=None, properties=None):
    evt = AnalyticsEvent(
        id=str(uuid.uuid4()),
        event_name=event_name,
        room_id=room_id,
        participant_id=participant_id,
        device_id=device_id,
        properties=json.dumps(properties) if properties else None,
    )
    db.add(evt)
    db.commit()


def get_or_create_daily_log(db: Session, room_id: str, log_date: str) -> DailyLog:
    dl = db.query(DailyLog).filter_by(room_id=room_id, date=log_date).first()
    if not dl:
        dl = DailyLog(id=str(uuid.uuid4()), room_id=room_id, date=log_date)
        db.add(dl)
        db.commit()
        db.refresh(dl)
    return dl


def current_hour_slot() -> str:
    return datetime.now().strftime("%H:00")


def generate_join_code() -> str:
    return str(random.randint(100000, 999999))


# ─── Pydantic 스키마 ───────────────────────────────────────────────────────────

class CreateRoomRequest(BaseModel):
    name: str
    mode: str  # friend | couple
    display_name: str
    device_id: str

class JoinRoomRequest(BaseModel):
    display_name: str
    device_id: str

class SelectQuestRequest(BaseModel):
    template_id: str
    participant_id: str

class AddReactionRequest(BaseModel):
    video_clip_id: str
    participant_id: str
    emoji: str

class LeaveRoomRequest(BaseModel):
    participant_id: str

class ShareRequest(BaseModel):
    participant_id: str
    action_type: str  # save | share

class UpdateQuestTemplateRequest(BaseModel):
    title: Optional[str] = None
    short_description: Optional[str] = None
    enabled: Optional[bool] = None


# ─── 방 API ───────────────────────────────────────────────────────────────────

@app.post("/api/rooms")
def create_room(req: CreateRoomRequest, db: Session = Depends(get_db)):
    # 참여 코드 생성 (중복 방지)
    for _ in range(10):
        code = generate_join_code()
        if not db.query(Room).filter_by(join_code=code).first():
            break

    room_id = str(uuid.uuid4())
    invite_url = f"snapchal://join/{code}"

    room = Room(
        id=room_id,
        name=req.name,
        mode=req.mode,
        join_code=code,
        invite_url=invite_url,
    )
    db.add(room)
    db.flush()

    participant = Participant(
        id=str(uuid.uuid4()),
        room_id=room_id,
        device_id=req.device_id,
        display_name=req.display_name,
    )
    db.add(participant)
    db.commit()

    log_event(db, "room_created", room_id=room_id, device_id=req.device_id)

    return {
        "room_id": room.id,
        "name": room.name,
        "mode": room.mode,
        "join_code": room.join_code,
        "invite_url": room.invite_url,
        "participant_id": participant.id,
    }


@app.get("/api/rooms/code/{join_code}")
def get_room_by_code(join_code: str, db: Session = Depends(get_db)):
    room = db.query(Room).filter_by(join_code=join_code, status="active").first()
    if not room:
        raise HTTPException(status_code=404, detail="방을 찾을 수 없어요")
    active_count = db.query(Participant).filter_by(room_id=room.id, status="active").count()
    if active_count >= room.max_participants:
        raise HTTPException(status_code=409, detail="다 찬 방이에요")
    return {
        "room_id": room.id,
        "name": room.name,
        "mode": room.mode,
        "join_code": room.join_code,
        "participant_count": active_count,
    }


@app.post("/api/rooms/{room_id}/join")
def join_room(room_id: str, req: JoinRoomRequest, db: Session = Depends(get_db)):
    room = db.query(Room).filter_by(id=room_id, status="active").first()
    if not room:
        raise HTTPException(status_code=404, detail="방을 찾을 수 없어요")
    active = db.query(Participant).filter_by(room_id=room_id, status="active").all()
    if len(active) >= room.max_participants:
        raise HTTPException(status_code=409, detail="다 찬 방이에요")

    # 동일 기기가 이미 참여 중인지 확인
    existing = db.query(Participant).filter_by(room_id=room_id, device_id=req.device_id, status="active").first()
    if existing:
        return {
            "participant_id": existing.id,
            "display_name": existing.display_name,
            "room_id": room_id,
            "room_name": room.name,
            "mode": room.mode,
        }

    participant = Participant(
        id=str(uuid.uuid4()),
        room_id=room_id,
        device_id=req.device_id,
        display_name=req.display_name,
    )
    db.add(participant)
    db.commit()

    log_event(db, "room_joined", room_id=room_id, device_id=req.device_id)

    return {
        "participant_id": participant.id,
        "display_name": participant.display_name,
        "room_id": room_id,
        "room_name": room.name,
        "mode": room.mode,
    }


@app.get("/api/rooms/{room_id}")
def get_room(room_id: str, db: Session = Depends(get_db)):
    room = db.query(Room).filter_by(id=room_id, status="active").first()
    if not room:
        raise HTTPException(status_code=404, detail="방을 찾을 수 없어요")
    participants = db.query(Participant).filter_by(room_id=room_id, status="active").all()
    return {
        "room_id": room.id,
        "name": room.name,
        "mode": room.mode,
        "join_code": room.join_code,
        "invite_url": room.invite_url,
        "participants": [{"id": p.id, "display_name": p.display_name} for p in participants],
    }


@app.post("/api/rooms/{room_id}/leave")
def leave_room(room_id: str, req: LeaveRoomRequest, db: Session = Depends(get_db)):
    p = db.query(Participant).filter_by(id=req.participant_id, room_id=room_id, status="active").first()
    if not p:
        raise HTTPException(status_code=404, detail="참여자를 찾을 수 없어요")
    p.status = "left"
    p.left_at = datetime.utcnow()

    # 공유 로그에서 숨김 처리
    clips = db.query(VideoClip).filter_by(participant_id=p.id, visible_in_shared_log=True).all()
    for clip in clips:
        clip.visible_in_shared_log = False
        clip.hidden_at = datetime.utcnow()

    db.commit()

    # 방에 active 참여자가 없으면 방 삭제
    remaining = db.query(Participant).filter_by(room_id=room_id, status="active").count()
    if remaining == 0:
        room = db.query(Room).filter_by(id=room_id).first()
        if room:
            room.status = "deleted"
            room.deleted_at = datetime.utcnow()
        db.commit()

    log_event(db, "room_left", room_id=room_id, participant_id=p.id)
    return {"success": True}


# ─── 퀘스트 API ───────────────────────────────────────────────────────────────

@app.get("/api/rooms/{room_id}/quest-candidates")
def get_quest_candidates(room_id: str, db: Session = Depends(get_db)):
    room = db.query(Room).filter_by(id=room_id, status="active").first()
    if not room:
        raise HTTPException(status_code=404, detail="방을 찾을 수 없어요")

    templates = db.query(QuestTemplate).filter_by(mode=room.mode, enabled=True).all()
    if len(templates) < 3:
        # fallback: 공통 퀘스트에서 채움
        fallbacks = db.query(QuestTemplate).filter_by(fallback=True, enabled=True).all()
        templates = list({t.id: t for t in (templates + fallbacks)}.values())

    candidates = random.sample(templates, min(3, len(templates)))

    log_event(db, "quest_candidates_viewed", room_id=room_id)

    return {
        "candidates": [
            {
                "template_id": t.id,
                "quest_id": t.quest_id,
                "title": t.title,
                "short_description": t.short_description,
                "tone": t.tone,
                "difficulty": t.difficulty,
                "tags": json.loads(t.tags) if t.tags else [],
            }
            for t in candidates
        ]
    }


@app.get("/api/rooms/{room_id}/today")
def get_today(room_id: str, db: Session = Depends(get_db)):
    today = date.today().isoformat()
    dl = db.query(DailyLog).filter_by(room_id=room_id, date=today).first()
    if not dl or not dl.daily_quest_id:
        return {"has_quest": False, "date": today, "daily_log_id": dl.id if dl else None}

    dq = db.query(DailyQuest).filter_by(id=dl.daily_quest_id).first()
    return {
        "has_quest": True,
        "date": today,
        "daily_log_id": dl.id,
        "quest": {
            "id": dq.id,
            "title": dq.title,
            "description": dq.description,
            "template_id": dq.template_id,
        }
    }


@app.post("/api/rooms/{room_id}/quest")
def select_quest(room_id: str, req: SelectQuestRequest, db: Session = Depends(get_db)):
    today = date.today().isoformat()
    dl = get_or_create_daily_log(db, room_id, today)

    # 이미 퀘스트가 선택된 경우
    if dl.daily_quest_id:
        existing_dq = db.query(DailyQuest).filter_by(id=dl.daily_quest_id).first()
        return {
            "daily_quest_id": existing_dq.id,
            "title": existing_dq.title,
            "already_selected": True,
        }

    template = db.query(QuestTemplate).filter_by(id=req.template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="퀘스트를 찾을 수 없어요")

    dq = DailyQuest(
        id=str(uuid.uuid4()),
        room_id=room_id,
        date=today,
        template_id=template.id,
        title=template.title,
        description=template.full_description,
        selected_by_participant_id=req.participant_id,
        locked=True,
    )
    db.add(dq)
    db.flush()

    dl.daily_quest_id = dq.id
    db.commit()

    log_event(db, "daily_quest_selected", room_id=room_id, participant_id=req.participant_id,
              properties={"quest_title": template.title})

    return {
        "daily_quest_id": dq.id,
        "title": dq.title,
        "already_selected": False,
    }


@app.get("/api/rooms/{room_id}/mission/{hour_slot}")
def get_mission(room_id: str, hour_slot: str, db: Session = Depends(get_db)):
    today = date.today().isoformat()
    dl = db.query(DailyLog).filter_by(room_id=room_id, date=today).first()
    if not dl or not dl.daily_quest_id:
        raise HTTPException(status_code=404, detail="오늘의 퀘스트가 없어요")

    dq = db.query(DailyQuest).filter_by(id=dl.daily_quest_id).first()
    mission = db.query(QuestMissionTemplate).filter_by(
        template_id=dq.template_id, hour_slot=hour_slot
    ).first()

    if not mission:
        raise HTTPException(status_code=404, detail="해당 시간대 미션이 없어요")

    log_event(db, "mission_viewed", room_id=room_id, properties={"hour_slot": hour_slot})

    return {
        "quest_title": dq.title,
        "hour_slot": hour_slot,
        "mission_title": mission.mission_title,
        "instruction": mission.instruction,
        "example": mission.example,
        "daily_quest_id": dq.id,
        "mission_id": mission.id,
    }


# ─── 로그 API ─────────────────────────────────────────────────────────────────

@app.get("/api/rooms/{room_id}/logs/{log_date}")
def get_log(room_id: str, log_date: str, db: Session = Depends(get_db)):
    room = db.query(Room).filter_by(id=room_id, status="active").first()
    if not room:
        raise HTTPException(status_code=404, detail="방을 찾을 수 없어요")

    dl = db.query(DailyLog).filter_by(room_id=room_id, date=log_date).first()
    participants = db.query(Participant).filter_by(room_id=room_id, status="active").all()

    quest_info = None
    clips_map = {}  # {participant_id: {hour_slot: clip_info}}

    if dl:
        if dl.daily_quest_id:
            dq = db.query(DailyQuest).filter_by(id=dl.daily_quest_id).first()
            quest_info = {"id": dq.id, "title": dq.title}

        clips = db.query(VideoClip).filter_by(
            daily_log_id=dl.id, visible_in_shared_log=True
        ).all()

        for clip in clips:
            if clip.participant_id not in clips_map:
                clips_map[clip.participant_id] = {}
            reactions = db.query(Reaction).filter_by(video_clip_id=clip.id).all()
            clips_map[clip.participant_id][clip.hour_slot] = {
                "id": clip.id,
                "hour_slot": clip.hour_slot,
                "file_url": f"/api/videos/{clip.id}/stream" if clip.upload_status == "uploaded" else None,
                "upload_status": clip.upload_status,
                "reactions": [{"emoji": r.emoji, "participant_id": r.participant_id} for r in reactions],
            }

    HOUR_SLOTS = [f"{h:02d}:00" for h in range(6, 24)]

    log_event(db, "log_viewed", room_id=room_id, properties={"date": log_date})

    return {
        "date": log_date,
        "daily_log_id": dl.id if dl else None,
        "quest": quest_info,
        "participants": [{"id": p.id, "display_name": p.display_name} for p in participants],
        "hour_slots": HOUR_SLOTS,
        "clips": clips_map,
    }


# ─── 영상 API ─────────────────────────────────────────────────────────────────

@app.post("/api/videos/upload")
async def upload_video(
    room_id: str = Form(...),
    participant_id: str = Form(...),
    daily_log_id: str = Form(...),
    daily_quest_id: str = Form(...),
    hour_slot: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    today = date.today().isoformat()

    # 같은 시간대에 이미 영상이 있는지 확인
    existing = db.query(VideoClip).filter_by(
        participant_id=participant_id,
        daily_log_id=daily_log_id,
        hour_slot=hour_slot,
        visible_in_shared_log=True,
    ).first()

    if existing:
        raise HTTPException(status_code=409, detail="이미 찍은 시간이에요")

    # 파일 저장
    clip_id = str(uuid.uuid4())
    ext = Path(file.filename).suffix if file.filename else ".webm"
    file_name = f"{clip_id}{ext}"
    file_path = UPLOAD_DIR / file_name

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    clip = VideoClip(
        id=clip_id,
        room_id=room_id,
        daily_log_id=daily_log_id,
        participant_id=participant_id,
        daily_quest_id=daily_quest_id,
        date=today,
        hour_slot=hour_slot,
        file_path=str(file_path),
        upload_status="uploaded",
        visible_in_shared_log=True,
        uploaded_at=datetime.utcnow(),
    )
    db.add(clip)
    db.commit()

    log_event(db, "video_upload_succeeded", room_id=room_id, participant_id=participant_id,
              properties={"hour_slot": hour_slot})

    return {"video_clip_id": clip.id, "success": True}


@app.get("/api/videos/{video_id}/stream")
def stream_video(video_id: str, db: Session = Depends(get_db)):
    clip = db.query(VideoClip).filter_by(id=video_id).first()
    if not clip or not clip.file_path:
        raise HTTPException(status_code=404, detail="영상을 찾을 수 없어요")
    return FileResponse(clip.file_path, media_type="video/webm")


@app.delete("/api/videos/{video_id}")
def delete_video(video_id: str, participant_id: str, db: Session = Depends(get_db)):
    clip = db.query(VideoClip).filter_by(id=video_id, participant_id=participant_id).first()
    if not clip:
        raise HTTPException(status_code=404, detail="영상을 찾을 수 없어요")

    today = date.today().isoformat()
    if clip.date != today:
        raise HTTPException(status_code=403, detail="오늘 올린 영상만 삭제할 수 있어요")

    clip.visible_in_shared_log = False
    clip.hidden_at = datetime.utcnow()
    db.commit()

    log_event(db, "video_deleted_from_shared_log", room_id=clip.room_id, participant_id=participant_id)

    return {"success": True}


# ─── 반응 API ─────────────────────────────────────────────────────────────────

@app.post("/api/reactions")
def add_reaction(req: AddReactionRequest, db: Session = Depends(get_db)):
    clip = db.query(VideoClip).filter_by(id=req.video_clip_id).first()
    if not clip:
        raise HTTPException(status_code=404, detail="영상을 찾을 수 없어요")

    reaction = Reaction(
        id=str(uuid.uuid4()),
        video_clip_id=req.video_clip_id,
        participant_id=req.participant_id,
        emoji=req.emoji,
    )
    db.add(reaction)
    db.commit()

    log_event(db, "reaction_added", room_id=clip.room_id, participant_id=req.participant_id,
              properties={"emoji": req.emoji})

    return {"reaction_id": reaction.id, "success": True}


# ─── 공유/저장 API ─────────────────────────────────────────────────────────────

@app.post("/api/rooms/{room_id}/share")
def record_share(room_id: str, req: ShareRequest, db: Session = Depends(get_db)):
    today = date.today().isoformat()
    dl = db.query(DailyLog).filter_by(room_id=room_id, date=today).first()

    record = ShareRecord(
        id=str(uuid.uuid4()),
        room_id=room_id,
        daily_log_id=dl.id if dl else None,
        participant_id=req.participant_id,
        action_type=req.action_type,
    )
    db.add(record)
    db.commit()

    event = "daily_log_saved" if req.action_type == "save" else "daily_log_shared"
    log_event(db, event, room_id=room_id, participant_id=req.participant_id)

    return {"success": True}


# ─── 퀘스트 관리 API (숨겨진 기능) ────────────────────────────────────────────

@app.get("/api/admin/quests")
def list_quests(db: Session = Depends(get_db)):
    templates = db.query(QuestTemplate).all()
    result = []
    for t in templates:
        missions = db.query(QuestMissionTemplate).filter_by(template_id=t.id).order_by(QuestMissionTemplate.order).all()
        result.append({
            "id": t.id,
            "quest_id": t.quest_id,
            "mode": t.mode,
            "title": t.title,
            "short_description": t.short_description,
            "enabled": t.enabled,
            "fallback": t.fallback,
            "missions": [
                {"hour_slot": m.hour_slot, "instruction": m.instruction, "example": m.example}
                for m in missions
            ]
        })
    return result


@app.patch("/api/admin/quests/{template_id}")
def update_quest(template_id: str, req: UpdateQuestTemplateRequest, db: Session = Depends(get_db)):
    t = db.query(QuestTemplate).filter_by(id=template_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="퀘스트를 찾을 수 없어요")
    if req.title is not None:
        t.title = req.title
    if req.short_description is not None:
        t.short_description = req.short_description
    if req.enabled is not None:
        t.enabled = req.enabled
    t.updated_at = datetime.utcnow()
    db.commit()
    return {"success": True}


# ─── 정적 파일 / SPA ──────────────────────────────────────────────────────────

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
def serve_index():
    return FileResponse(str(STATIC_DIR / "index.html"))

@app.get("/{full_path:path}")
def serve_spa(full_path: str):
    # API가 아니면 index.html 반환 (SPA)
    if full_path.startswith("api/") or full_path.startswith("static/"):
        raise HTTPException(status_code=404)
    index = STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index))
    raise HTTPException(status_code=404)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
