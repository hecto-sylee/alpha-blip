"""Auth (guest sessions) — F: common."""
from __future__ import annotations

import json
import secrets

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models import Pet, User
from ..schemas import GuestSignupReq, GuestSignupRes, MeRes, PetSummary
from ..utils.events import log_event
from ..utils.jsonx import loads_list

router = APIRouter(tags=["auth"])


@router.post("/auth/guest", response_model=GuestSignupRes, status_code=201)
def guest_signup(body: GuestSignupReq, db: Session = Depends(get_db)) -> GuestSignupRes:
    token = secrets.token_urlsafe(32)
    user = User(nickname=body.nickname, auth_token=token)
    db.add(user)
    db.flush()
    log_event(db, "guest_signup", user_id=user.id, payload={"nickname": body.nickname})
    db.commit()
    return GuestSignupRes(user_id=user.id, auth_token=token)


@router.get("/auth/me", response_model=MeRes)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> MeRes:
    pets = db.query(Pet).filter(Pet.user_id == user.id).all()
    return MeRes(
        id=user.id,
        nickname=user.nickname,
        profile_image_url=user.profile_image_url,
        pets=[
            PetSummary(
                id=p.id,
                name=p.name,
                breed=p.breed,
                photo_url=p.photo_url,
                size=p.size,
                personality_tags=loads_list(p.personality_tags),
            )
            for p in pets
        ],
    )
