"""Pet diary (W6): standalone mood/activity/text entries per (user, date).

신규 모델 PetDiary 의 CRUD. 모든 엔드포인트는 인증 필요(get_current_user) +
본인 소유 가드(owner only). activity_tags 는 JSON 문자열(Text)로 보관하고
응답에서는 list[str] 로 풀어 준다.
"""
from __future__ import annotations

import json
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models import Pet, PetDiary, User
from ..schemas import (
    PetDiaryCreateReq,
    PetDiaryCreateRes,
    PetDiaryListRes,
    PetDiaryOut,
    PetDiaryUpdateReq,
)

router = APIRouter(tags=["pet-diary"])


def _tags_to_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return [str(t) for t in data] if isinstance(data, list) else []
    except (ValueError, TypeError):
        return []


def serialize_diary(d: PetDiary) -> PetDiaryOut:
    return PetDiaryOut(
        id=d.id,
        pet_id=d.pet_id,
        diary_date=d.diary_date,
        mood=d.mood,
        activity_tags=_tags_to_list(d.activity_tags),
        text=d.text,
        created_at=d.created_at,
    )


def _resolve_pet_id(db: Session, user: User, pet_id: str | None) -> str | None:
    """본인 펫만 허용. 미지정 시 대표 펫(가장 먼저 등록한 펫)으로 기본 설정."""
    if pet_id:
        pet = db.get(Pet, pet_id)
        if pet is None or pet.user_id != user.id:
            raise HTTPException(status_code=404, detail="pet not found")
        return pet_id
    pet = (
        db.query(Pet)
        .filter(Pet.user_id == user.id)
        .order_by(Pet.created_at)
        .first()
    )
    return pet.id if pet else None


@router.post("/pet-diary", response_model=PetDiaryCreateRes, status_code=201)
def create_pet_diary(
    body: PetDiaryCreateReq,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PetDiaryCreateRes:
    diary = PetDiary(
        user_id=user.id,
        pet_id=_resolve_pet_id(db, user, body.pet_id),
        diary_date=body.diary_date,
        mood=body.mood,
        activity_tags=json.dumps(body.activity_tags or [], ensure_ascii=False),
        text=body.text,
    )
    db.add(diary)
    db.commit()
    return PetDiaryCreateRes(pet_diary_id=diary.id)


@router.get("/pet-diary", response_model=PetDiaryListRes)
def list_pet_diaries(
    from_: date | None = Query(None, alias="from"),
    to: date | None = Query(None),
    date_: date | None = Query(None, alias="date"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PetDiaryListRes:
    q = db.query(PetDiary).filter(PetDiary.user_id == user.id)
    if date_:
        q = q.filter(PetDiary.diary_date == date_)
    else:
        if from_:
            q = q.filter(PetDiary.diary_date >= from_)
        if to:
            q = q.filter(PetDiary.diary_date <= to)
    rows = q.order_by(PetDiary.diary_date.desc(), PetDiary.created_at.desc()).all()
    return PetDiaryListRes(diaries=[serialize_diary(d) for d in rows])


def _owned(db: Session, diary_id: str, user: User) -> PetDiary:
    diary = db.get(PetDiary, diary_id)
    if diary is None:
        raise HTTPException(status_code=404, detail="pet diary not found")
    if diary.user_id != user.id:
        raise HTTPException(status_code=403, detail="not your pet diary")
    return diary


@router.get("/pet-diary/{diary_id}", response_model=PetDiaryOut)
def get_pet_diary(
    diary_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PetDiaryOut:
    return serialize_diary(_owned(db, diary_id, user))


@router.patch("/pet-diary/{diary_id}", response_model=PetDiaryOut)
def update_pet_diary(
    diary_id: str,
    body: PetDiaryUpdateReq,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PetDiaryOut:
    diary = _owned(db, diary_id, user)
    data = body.model_dump(exclude_unset=True)
    if "mood" in data and data["mood"] is not None:
        diary.mood = data["mood"]
    if "activity_tags" in data and data["activity_tags"] is not None:
        diary.activity_tags = json.dumps(data["activity_tags"], ensure_ascii=False)
    if "text" in data:
        diary.text = data["text"]
    db.commit()
    db.refresh(diary)
    return serialize_diary(diary)


@router.delete("/pet-diary/{diary_id}")
def delete_pet_diary(
    diary_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    diary = _owned(db, diary_id, user)
    db.delete(diary)
    db.commit()
    return {"ok": True}
