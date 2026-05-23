"""Database engine and session management."""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.persistence.models import Base
from langweave.config import load_dotenv

logger = logging.getLogger(__name__)


def _database_url() -> str:
    load_dotenv()
    url = os.environ.get("LANGWEAVE_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not url:
        msg = (
            "LANGWEAVE_DATABASE_URL is not set. "
            "Example: mysql+pymysql://user:pass@host:3306/dbname"
        )
        raise RuntimeError(msg)
    return url


def _create_engine(url: str) -> Engine:
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        pool_recycle=3600,
    )


@lru_cache
def get_engine(url: str | None = None) -> Engine:
    return _create_engine(url or _database_url())


@lru_cache
def get_session_factory(url: str | None = None) -> sessionmaker[Session]:
    return sessionmaker(
        bind=get_engine(url),
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )


def init_database() -> None:
    url = _database_url()
    engine = get_engine(url)
    Base.metadata.create_all(bind=engine)
    logger.info("Database connected: %s", url.partition("://")[0] + "://***")


# ---------------------------------------------------------------------------
# Table structure
# ---------------------------------------------------------------------------
#
# c_users
# ──────────────────────────────────────────────
#  id            INT          PK AUTO_INCREMENT
#  username      VARCHAR(64)  UNIQUE INDEX
#  password_hash VARCHAR(255)
#  created_at    DATETIME
#
# c_conversations
# ──────────────────────────────────────────────
#  id            INT          PK AUTO_INCREMENT
#  user_id       INT          INDEX
#  agent_name    VARCHAR(32)  DEFAULT 'emotional'
#  thread_id     VARCHAR(64)  UNIQUE INDEX
#  title         VARCHAR(128) DEFAULT '新对话'
#  created_at    DATETIME
#  updated_at    DATETIME
#
# c_messages
# ──────────────────────────────────────────────
#  id              INT          PK AUTO_INCREMENT
#  conversation_id INT          INDEX
#  role            VARCHAR(16)
#  content         TEXT
#  created_at      DATETIME
#
# Notes:
# - No foreign keys (all logical references via indexed columns)
# - No unique constraint on (user_id, agent_name) — multiple conversations allowed
# ---------------------------------------------------------------------------


def get_db_session() -> Generator[Session, None, None]:
    session = get_session_factory()()
    session.execute(text("SELECT 1"))
    try:
        yield session
    finally:
        session.close()


def reset_database_caches() -> None:
    get_session_factory.cache_clear()
    get_engine.cache_clear()
