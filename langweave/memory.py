"""Multi-turn conversation memory via LangGraph checkpointer.

Supports both in-memory (default) and MySQL-backed persistence.
When ``LANGWEAVE_DATABASE_URL`` (or ``DATABASE_URL``) starts with ``mysql``
the checkpointer automatically uses AIOMySQLSaver (async) for compatibility
with the async FastAPI runtime.
"""

from __future__ import annotations

import logging
import os
import uuid
from functools import lru_cache
from typing import Any

from langchain_core.messages import BaseMessage

logger = logging.getLogger(__name__)
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph

from langweave.config import load_dotenv


def _is_mysql_url(url: str) -> bool:
    return url.startswith("mysql") or url.startswith("mysql+pymysql:")


def _resolve_url() -> str:
    load_dotenv()
    return (
        os.environ.get("LANGWEAVE_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
        or ""
    )


def _normalize_mysql_url(raw_url: str) -> str:
    return raw_url.replace("mysql+pymysql:", "mysql:", 1)


@lru_cache
def get_checkpointer() -> BaseCheckpointSaver:
    """Return a shared checkpointer.

    When MySQL is configured, returns an AIOMySQLSaver wrapper whose
    connection is lazily initialised on first async use.
    Otherwise returns a plain ``MemorySaver``.

    This function is **sync** so it can be used in agent builder etc.
    For MySQL the actual async connection creation is deferred to the
    first ``await`` call on the checkpointer.
    """
    url = _resolve_url()
    if not _is_mysql_url(url):
        return MemorySaver()

    return _LazyAsyncCheckpointer(url)


class _LazyAsyncCheckpointer(BaseCheckpointSaver):
    """Deferred async MySQL checkpointer.

    ``AIOMySQLSaver`` requires an ``await`` to create its connection, but
    ``get_checkpointer()`` is called from sync agent builder code.
    This wrapper creates the real checkpointer on the first async call.
    """

    def __init__(self, url: str) -> None:
        super().__init__()
        self._url = url
        self._real: BaseCheckpointSaver | None = None

    async def _ensure(self) -> BaseCheckpointSaver:
        if self._real is not None:
            return self._real
        saver = await _create_async_mysql_checkpointer(self._url)
        self._real = saver
        return saver

    async def aget_tuple(self, config: dict[str, Any]) -> Any:
        return await (await self._ensure()).aget_tuple(config)

    async def aput(self, config: dict[str, Any], checkpoint: Any, metadata: Any, new_versions: Any) -> Any:
        return await (await self._ensure()).aput(config, checkpoint, metadata, new_versions)

    async def aput_writes(self, config: dict[str, Any], writes: Any, task_id: str) -> None:
        return await (await self._ensure()).aput_writes(config, writes, task_id)

    async def alist(self, config: dict[str, Any], *, filter: Any = None, before: Any = None, limit: Any = None) -> Any:
        return await (await self._ensure()).alist(config, filter=filter, before=before, limit=limit)

    def get_tuple(self, config: dict[str, Any]) -> Any:
        raise NotImplementedError("_LazyAsyncCheckpointer does not support sync get_tuple; use aget_tuple")

    def put(self, config: dict[str, Any], checkpoint: Any, metadata: Any, new_versions: Any) -> Any:
        raise NotImplementedError("_LazyAsyncCheckpointer does not support sync put; use aput")

    def put_writes(self, config: dict[str, Any], writes: Any, task_id: str) -> None:
        raise NotImplementedError("_LazyAsyncCheckpointer does not support sync put_writes; use aput_writes")

    def list(self, config: dict[str, Any], *, filter: Any = None, before: Any = None, limit: Any = None) -> Any:
        raise NotImplementedError("_LazyAsyncCheckpointer does not support sync list; use alist")


async def _create_async_mysql_checkpointer(url: str) -> BaseCheckpointSaver:
    """Create an AIOMySQLSaver with an async connection."""
    try:
        from langgraph.checkpoint.mysql.aio import AIOMySQLSaver as _AIOMySQLSaver
    except ImportError as exc:
        msg = (
            "MySQL checkpointer requires langgraph-checkpoint-mysql and aiomysql. "
            "Install them with: pip install langgraph-checkpoint-mysql aiomysql"
        )
        raise ImportError(msg) from exc

    import aiomysql

    AIOMySQLSaver = _AIOMySQLSaver
    conn_url = _normalize_mysql_url(url)

    conn = await aiomysql.connect(
        **AIOMySQLSaver.parse_conn_string(conn_url),
        autocommit=True,
    )

    # Match the session collation to the existing checkpoints table (if any)
    # so that WHERE clause comparisons don't fail with "Illegal mix of
    # collations".  If the table doesn't exist yet, fall back to the
    # database default, then to utf8mb4_0900_ai_ci (MySQL 8 default).
    async with conn.cursor(aiomysql.DictCursor) as cur:
        await cur.execute(
            "SELECT COALESCE("
            "(SELECT TABLE_COLLATION FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'checkpoints'), "
            "(SELECT DEFAULT_COLLATION_NAME FROM information_schema.SCHEMATA "
            "WHERE SCHEMA_NAME = DATABASE()), "
            "'utf8mb4_0900_ai_ci') AS collation"
        )
        row = await cur.fetchone()
        collation = row["collation"] if row else "utf8mb4_0900_ai_ci"
        await cur.execute(f"SET NAMES utf8mb4 COLLATE {collation}")
        await cur.execute(f"SET collation_connection = {collation}")

    saver = AIOMySQLSaver(conn=conn)
    # Suppress the benign "Table already exists" warning on setup.
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=Warning)
        await saver.setup()
    return saver


def resolve_thread_id(thread_id: str | None) -> str:
    return thread_id or str(uuid.uuid4())


def thread_config(thread_id: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": thread_id}}


async def aget_thread_messages(
    graph: CompiledStateGraph[Any, Any, Any, Any],
    thread_id: str,
) -> list[BaseMessage]:
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
    await graph.aupdate_state(
        thread_config(thread_id),
        {"messages": []},
    )
