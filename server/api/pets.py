"""Pets (F-02)."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models import Pet, User
from ..schemas import PetCreateReq, PetCreateRes, PetListRes, PetRes, PetUpdateReq
from ..utils.events import log_event

router = APIRouter(tags=["pets"])


def _loads(value: str | None) -> list:
    if not value:
        return []
    try:
        return json.loads(value)
    except (ValueError, TypeError):
        return []


def _loads_obj(value: str | None) -> dict | None:
    if not value:
        return None
    try:
        v = json.loads(value)
        return v if isinstance(v, dict) else None
    except (ValueError, TypeError):
        return None


def _to_res(pet: Pet) -> PetRes:
    return PetRes(
        id=pet.id,
        name=pet.name,
        photo_url=pet.photo_url,
        breed=pet.breed,
        age_months=pet.age_months,
        gender=pet.gender,
        size=pet.size,
        is_neutered=pet.is_neutered,
        personality_tags=_loads(pet.personality_tags),
        sociality=pet.sociality,
        activity_level=pet.activity_level,
        walk_style=pet.walk_style,
        preferred_partner_size=_loads(pet.preferred_partner_size),
        caution_notes=pet.caution_notes,
        appearance=_loads_obj(pet.appearance_json),
    )


@router.post("/pets", response_model=PetCreateRes, status_code=201)
def create_pet(
    body: PetCreateReq,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PetCreateRes:
    pet = Pet(
        user_id=user.id,
        name=body.name,
        photo_url=body.photo_url,
        breed=body.breed,
        age_months=body.age_months,
        gender=body.gender,
        size=body.size,
        is_neutered=body.is_neutered,
        personality_tags=json.dumps(body.personality_tags, ensure_ascii=False)
        if body.personality_tags is not None
        else None,
        sociality=body.sociality,
        activity_level=body.activity_level,
        walk_style=body.walk_style,
        preferred_partner_size=json.dumps(body.preferred_partner_size, ensure_ascii=False)
        if body.preferred_partner_size is not None
        else None,
        caution_notes=body.caution_notes,
        appearance_json=json.dumps(body.appearance, ensure_ascii=False)
        if body.appearance is not None
        else None,
    )
    db.add(pet)
    db.flush()
    log_event(db, "pet_create", user_id=user.id, payload={"pet_id": pet.id})
    db.commit()
    return PetCreateRes(pet_id=pet.id)


@router.get("/pets", response_model=PetListRes)
def list_pets(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PetListRes:
    pets = (
        db.query(Pet)
        .filter(Pet.user_id == user.id)
        .order_by(Pet.created_at.asc())
        .all()
    )
    return PetListRes(pets=[_to_res(p) for p in pets])


@router.get("/pets/{pet_id}", response_model=PetRes)
def get_pet(pet_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> PetRes:
    pet = db.get(Pet, pet_id)
    if pet is None:
        raise HTTPException(status_code=404, detail="pet not found")
    return _to_res(pet)


@router.patch("/pets/{pet_id}", response_model=PetRes)
def update_pet(
    pet_id: str,
    body: PetUpdateReq,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PetRes:
    pet = db.get(Pet, pet_id)
    if pet is None:
        raise HTTPException(status_code=404, detail="pet not found")
    if pet.user_id != user.id:
        raise HTTPException(status_code=403, detail="not your pet")

    data = body.model_dump(exclude_unset=True)
    if "appearance" in data:  # DTO명(appearance) → 컬럼명(appearance_json), 객체→JSON
        appearance = data.pop("appearance")
        pet.appearance_json = json.dumps(appearance, ensure_ascii=False) if appearance is not None else None
    for field in ("personality_tags", "preferred_partner_size"):
        if field in data and data[field] is not None:
            data[field] = json.dumps(data[field], ensure_ascii=False)
    for key, value in data.items():
        setattr(pet, key, value)
    db.commit()
    db.refresh(pet)
    return _to_res(pet)
