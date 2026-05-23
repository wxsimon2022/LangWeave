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
    elif url.startswith("mysql"):
        kwargs["pool_size"] = 5
        kwargs["max_overflow"] = 10
        kwargs["pool_recycle"] = 3600
    return create_engine(url, **kwargs)


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
    _drop_all_tables(engine)
    Base.metadata.create_all(bind=engine)
    if url == SQLITE_FALLBACK_URL:
        logger.warning(
            "LANGWEAVE_DATABASE_URL is not set; using local SQLite at %s",
            SQLITE_FALLBACK_URL,
        )
    else:
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


def _table_exists(engine: Engine, table: str) -> bool:
    dialect = engine.dialect.name
    try:
        with engine.connect() as conn:
            if dialect == "sqlite":
                rows = conn.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table' AND name=:t"),
                    {"t": table},
                ).all()
                return len(rows) > 0
            else:
                result = conn.execute(
                    text(
                        "SELECT TABLE_NAME FROM information_schema.TABLES "
                        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t"
                    ),
                    {"t": table},
                )
                return result.first() is not None
    except SQLAlchemyError:
        return False


def _drop_all_tables(engine: Engine) -> None:
    """Drop all tracked tables so they can be recreated from models."""
    tables = [
        "c_messages", "c_conversations", "c_users",
        "chat_messages", "chat_conversations", "chat_users",
        "conversations", "users",
    ]
    dialect = engine.dialect.name

    # Use a raw connection to avoid transactional semantics issues with DDL.
    conn = engine.raw_connection()
    try:
        cursor = conn.cursor()
        if dialect != "sqlite":
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        for table in tables:
            if _table_exists(engine, table):
                cursor.execute(f"DROP TABLE IF EXISTS {table}")
                logger.info("Dropped table `%s`", table)
            else:
                logger.debug("Table `%s` does not exist, skipping", table)
        if dialect != "sqlite":
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        conn.commit()
    except Exception as exc:
        conn.rollback()
        logger.warning("Failed to drop tables: %s", exc)
    finally:
        conn.close()


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
