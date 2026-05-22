"""Multi-turn conversation memory via LangGraph checkpointer.

Supports both in-memory (default) and MySQL-backed persistence.
When ``LANGWEAVE_DATABASE_URL`` (or ``DATABASE_URL``) starts with ``mysql``
the checkpointer automatically uses PyMySQLSaver.
"""

from __future__ import annotations

import os
import uuid
from functools import lru_cache
from typing import Any

from langchain_core.messages import BaseMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph

from langweave.config import load_dotenv


def _is_mysql_url(url: str) -> bool:
    return url.startswith("mysql") or url.startswith("mysql+pymysql:")


@lru_cache
def get_checkpointer() -> BaseCheckpointSaver:
    """Return a shared checkpointer backed by in-memory or MySQL storage.

    When ``LANGWEAVE_DATABASE_URL`` (or ``DATABASE_URL``) starts with
    ``mysql`` or ``mysql+pymysql:`` the returned checkpointer persists
    state in MySQL via pymysql. Otherwise a plain ``MemorySaver`` is used.
    """
    load_dotenv()
    url = (
        os.environ.get("LANGWEAVE_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
        or ""
    )
    if _is_mysql_url(url):
        return _create_mysql_checkpointer(url)
    return MemorySaver()


def _normalize_mysql_url(raw_url: str) -> str:
    """Convert a SQLAlchemy-style URL to the format expected by PyMySQLSaver."""
    # SQLAlchemy: mysql+pymysql://user:pass@host:port/db
    # pymysql:    mysql://user:pass@host:port/db
    return raw_url.replace("mysql+pymysql:", "mysql:", 1)


def _create_mysql_checkpointer(url: str) -> BaseCheckpointSaver:
    """Build a PyMySQLSaver from a MySQL connection string and run setup."""
    try:
        import pymysql
        from langgraph.checkpoint.mysql.pymysql import PyMySQLSaver as _PyMySQLSaver
    except ImportError as exc:
        msg = (
            "MySQL checkpointer requires langgraph-checkpoint-mysql and pymysql. "
            "Install them with: pip install langgraph-checkpoint-mysql pymysql"
        )
        raise ImportError(msg) from exc

    PyMySQLSaver = _PyMySQLSaver

    conn_url = _normalize_mysql_url(url)
    conn = pymysql.connect(
        **PyMySQLSaver.parse_conn_string(conn_url),
        autocommit=True,
    )
    checkpointer = PyMySQLSaver(conn)
    checkpointer.setup()
    return checkpointer


def resolve_thread_id(thread_id: str | None) -> str:
    """Use provided session id or create a new one for multi-turn memory."""
    return thread_id or str(uuid.uuid4())


def thread_config(thread_id: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": thread_id}}


async def aget_thread_messages(
    graph: CompiledStateGraph[Any, Any, Any, Any],
    thread_id: str,
) -> list[BaseMessage]:
    """Load message history for a conversation thread."""
    snapshot = await graph.aget_state(thread_config(thread_id))
    if snapshot is None or not snapshot.values:
        return []
    messages = snapshot.values.get("messages", [])
    return list(messages) if messages else []


def get_thread_messages(
    graph: CompiledStateGraph[Any, Any, Any, Any],
    thread_id: str,
) -> list[BaseMessage]:
    snapshot = graph.get_state(thread_config(thread_id))
    if snapshot is None or not snapshot.values:
        return []
    messages = snapshot.values.get("messages", [])
    return list(messages) if messages else []


async def aclear_thread(
    graph: CompiledStateGraph[Any, Any, Any, Any],
    thread_id: str,
) -> None:
    """Clear checkpointed state for a thread (new conversation)."""
    await graph.aupdate_state(
        thread_config(thread_id),
        {"messages": []},
    )
