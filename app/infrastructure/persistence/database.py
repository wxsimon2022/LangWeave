"""Database engine and session management."""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.exc import SQLAlchemyError

from app.infrastructure.persistence.models import Base
from langweave.config import load_dotenv
from app.constants import SQLITE_FALLBACK_URL

logger = logging.getLogger(__name__)


def _database_url() -> str:
    load_dotenv()
    return (
        os.environ.get("LANGWEAVE_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
        or SQLITE_FALLBACK_URL
    )


def _create_engine(url: str) -> Engine:
    kwargs: dict[str, object] = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(url, **kwargs)


@lru_cache
def get_engine(url: str | None = None) -> Engine:
    """Return the shared SQLAlchemy engine."""
    return _create_engine(url or _database_url())


@lru_cache
def get_session_factory(url: str | None = None) -> sessionmaker[Session]:
    """Return the shared SQLAlchemy session factory."""
    return sessionmaker(
        bind=get_engine(url),
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )


def init_database() -> None:
    """Create tables if they do not exist."""
    url = _database_url()
    engine = get_engine(url)
    Base.metadata.create_all(bind=engine)
    if url == SQLITE_FALLBACK_URL:
        logger.warning(
            "LANGWEAVE_DATABASE_URL is not set; using local SQLite at %s",
            SQLITE_FALLBACK_URL,
        )


def get_db_session() -> Generator[Session, None, None]:
    """FastAPI dependency for a transactional DB session."""
    session = get_session_factory()()
    session.execute(text("SELECT 1"))
    try:
        yield session
    finally:
        session.close()


def reset_database_caches() -> None:
    """Test helper to rebuild engine/session when env changes."""
    get_session_factory.cache_clear()
    get_engine.cache_clear()
