"""SQLAlchemy engine/session.

SQLite by default (walk.db); set ``LETSPAW_DATABASE_URL`` to any SQLAlchemy URL
(e.g. a hosted Postgres) to switch to a cloud DB without code changes. A small
dialect-aware schema patcher stands in for Alembic at this prototype stage.
"""
from __future__ import annotations

import os

from sqlalchemy import inspect, text
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEFAULT_SQLITE = f"sqlite:///{os.environ.get('LETSPAW_DB') or os.path.join(BASE_DIR, 'walk.db')}"
DATABASE_URL = os.environ.get("LETSPAW_DATABASE_URL") or _DEFAULT_SQLITE

IS_SQLITE = DATABASE_URL.startswith("sqlite")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if IS_SQLITE else {},
    pool_pre_ping=not IS_SQLITE,
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
    """Add columns introduced after a DB was first created.

    Stands in for Alembic on dev/prototype DBs. New tables are handled by
    ``create_all``; this only patches missing *columns* on existing tables.
    Dialect-aware so the same DDL works on SQLite and Postgres.
    """
    inspector = inspect(engine)
    dialect = engine.dialect.name  # "sqlite" | "postgresql" | ...
    false_lit = "FALSE" if dialect == "postgresql" else "0"

    # (table, column, column-DDL). Appended to as new features land.
    additions = [
        ("users", "is_mock", f"BOOLEAN DEFAULT {false_lit} NOT NULL"),
        ("users", "login_id", "VARCHAR"),
        ("users", "points", "INTEGER DEFAULT 0 NOT NULL"),
        ("users", "kakao_id", "VARCHAR"),
        ("users", "is_kakao", f"BOOLEAN DEFAULT {false_lit} NOT NULL"),
        ("pets", "appearance_json", "TEXT"),
        ("records", "merged_path", "VARCHAR"),
        ("match_sessions", "a_met", f"BOOLEAN DEFAULT {false_lit} NOT NULL"),
        ("match_sessions", "b_met", f"BOOLEAN DEFAULT {false_lit} NOT NULL"),
    ]

    for table, column, ddl in additions:
        if not inspector.has_table(table):
            continue
        cols = {c["name"] for c in inspector.get_columns(table)}
        if column in cols:
            continue
        with engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))
