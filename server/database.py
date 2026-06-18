"""SQLAlchemy engine/session for SQLite (walk.db)."""
from __future__ import annotations

import os

from sqlalchemy import inspect, text
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "walk.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    """Create all tables. Imports models so metadata is populated."""
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_dev_schema()


def _ensure_dev_schema() -> None:
    """Small SQLite schema patcher for MVP dev DBs without Alembic."""
    inspector = inspect(engine)
    if not inspector.has_table("users"):
        return
    user_cols = {col["name"] for col in inspector.get_columns("users")}
    if "is_mock" not in user_cols:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN is_mock BOOLEAN DEFAULT 0 NOT NULL"))
