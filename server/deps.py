"""Shared FastAPI dependencies: DB session + current user (guest token)."""
from __future__ import annotations

from typing import Generator

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import User


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    user = db.query(User).filter(User.auth_token == token).first()
    if user is None:
        raise HTTPException(status_code=401, detail="invalid token")
    return user
