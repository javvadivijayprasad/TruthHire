"""Database engine + session (TH-005). SQLite by default (file, zero setup),
PostgreSQL-ready via DATABASE_URL (e.g. postgresql+psycopg://user:pw@host/db)."""
from __future__ import annotations
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import StaticPool

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///truthhire.db")


def _make_engine():
    if DATABASE_URL.startswith("sqlite"):
        if DATABASE_URL in ("sqlite://", "sqlite:///:memory:"):
            return create_engine(DATABASE_URL, connect_args={"check_same_thread": False},
                                 poolclass=StaticPool)
        return create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    return create_engine(DATABASE_URL, pool_pre_ping=True)


engine = _make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    """Create tables if absent (dev/sqlite). Production uses Alembic migrations."""
    import app.models  # noqa: F401  (register models on Base.metadata)
    Base.metadata.create_all(engine)
