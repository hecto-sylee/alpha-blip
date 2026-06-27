"""Auth (guest sessions + Kakao OAuth) — F: common."""
from __future__ import annotations

import json
import os
import secrets
import urllib.parse
import urllib.request

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models import Pet, User
from ..schemas import (
    GuestSignupReq,
    GuestSignupRes,
    KakaoLoginReq,
    KakaoLoginRes,
    KakaoUrlRes,
    LoginReq,
    LoginRes,
    MeRes,
    PetSummary,
)
from ..utils.events import log_event
from ..utils.jsonx import loads_list

router = APIRouter(tags=["auth"])

# 카카오 OAuth 설정(자격증명은 환경변수 — 코드에 하드코딩 금지)
KAKAO_REST_KEY = os.environ.get("KAKAO_REST_API_KEY", "")
KAKAO_REDIRECT = os.environ.get("KAKAO_REDIRECT_URI", "")
KAKAO_SECRET = os.environ.get("KAKAO_CLIENT_SECRET", "")


def _kakao_enabled() -> bool:
    return bool(KAKAO_REST_KEY and KAKAO_REDIRECT)


def _http_post(url: str, data: dict) -> dict:
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())


def _http_get(url: str, token: str) -> dict:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())


@router.post("/auth/login", response_model=LoginRes, status_code=201)
def login(body: LoginReq, db: Session = Depends(get_db)) -> LoginRes:
    """아이디 기반 로그인(PoC, 비밀번호 없음). 같은 아이디면 같은 계정으로 복귀한다."""
    login_id = body.login_id.strip().lower()
    if not login_id:
        raise HTTPException(status_code=400, detail="아이디를 입력해 주세요")
    user = db.query(User).filter(User.login_id == login_id).first()
    is_new = user is None
    if user is None:
        nickname = (body.nickname or "").strip() or body.login_id.strip()
        user = User(nickname=nickname, login_id=login_id, auth_token=secrets.token_urlsafe(32))
        db.add(user)
        db.flush()
        log_event(db, "login_signup", user_id=user.id, payload={"login_id": login_id})
    elif body.nickname and body.nickname.strip():
        user.nickname = body.nickname.strip()  # 닉네임을 새로 주면 갱신
    db.commit()
    return LoginRes(user_id=user.id, auth_token=user.auth_token, nickname=user.nickname, is_new=is_new)


@router.get("/auth/kakao/url", response_model=KakaoUrlRes)
def kakao_url() -> KakaoUrlRes:
    if not _kakao_enabled():
        return KakaoUrlRes(enabled=False)
    q = urllib.parse.urlencode({
        "client_id": KAKAO_REST_KEY,
        "redirect_uri": KAKAO_REDIRECT,
        "response_type": "code",
    })
    return KakaoUrlRes(enabled=True, authorize_url=f"https://kauth.kakao.com/oauth/authorize?{q}")


@router.post("/auth/kakao", response_model=KakaoLoginRes, status_code=201)
def kakao_login(body: KakaoLoginReq, db: Session = Depends(get_db)) -> KakaoLoginRes:
    if not _kakao_enabled():
        raise HTTPException(status_code=400, detail="kakao login is not configured")
    try:
        token_data = {
            "grant_type": "authorization_code",
            "client_id": KAKAO_REST_KEY,
            "redirect_uri": body.redirect_uri or KAKAO_REDIRECT,
            "code": body.code,
        }
        if KAKAO_SECRET:
            token_data["client_secret"] = KAKAO_SECRET
        tok = _http_post("https://kauth.kakao.com/oauth/token", token_data)
        access = tok["access_token"]
        profile = _http_get("https://kapi.kakao.com/v2/user/me", access)
    except Exception as e:  # 네트워크/카카오 오류
        raise HTTPException(status_code=502, detail=f"kakao auth failed: {e}")

    kakao_id = str(profile.get("id"))
    nick = (((profile.get("kakao_account") or {}).get("profile") or {}).get("nickname")
            or f"카카오{kakao_id[-4:]}")
    user = db.query(User).filter(User.kakao_id == kakao_id).first()
    is_new = user is None
    if user is None:
        user = User(nickname=nick, auth_token=secrets.token_urlsafe(32), kakao_id=kakao_id, is_kakao=True)
        db.add(user)
        db.flush()
        log_event(db, "kakao_signup", user_id=user.id, payload={"kakao_id": kakao_id})
    db.commit()
    return KakaoLoginRes(user_id=user.id, auth_token=user.auth_token, nickname=user.nickname, is_new=is_new)


def _appearance(value: str | None) -> dict | None:
    if not value:
        return None
    try:
        v = json.loads(value)
        return v if isinstance(v, dict) else None
    except (ValueError, TypeError):
        return None


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
        points=user.points or 0,
        pets=[
            PetSummary(
                id=p.id,
                name=p.name,
                breed=p.breed,
                photo_url=p.photo_url,
                size=p.size,
                personality_tags=loads_list(p.personality_tags),
                appearance=_appearance(p.appearance_json),
            )
            for p in pets
        ],
    )
