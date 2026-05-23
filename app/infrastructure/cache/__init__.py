"""Redis connection management and cache/session helpers.

Usage:
    from app.infrastructure.cache import get_redis

    redis = get_redis()
    await redis.set("key", "value", ex=60)

Sync client (for use in FastAPI sync dependencies):
    from app.infrastructure.cache import get_sync_redis

    r = get_sync_redis()
    r.get("key")
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


@lru_cache
def _redis_url() -> str | None:
    """Read Redis URL from environment."""
    url = os.environ.get("LANGWEAVE_REDIS_URL") or os.environ.get("REDIS_URL") or None
    return url


def is_redis_available() -> bool:
    """Check if Redis is configured in the environment."""
    return _redis_url() is not None


@lru_cache
def get_redis() -> aioredis.Redis | None:
    """Get an async Redis client instance (cached, singleton per process).

    Returns ``None`` if Redis is not configured.
    The client connects lazily — first command will establish the connection.
    """
    url = _redis_url()
    if not url:
        logger.info("Redis not configured — Redis features disabled")
        return None
    logger.debug("Redis configured")
    return aioredis.from_url(
        url,
        encoding="utf-8",
        decode_responses=True,
        socket_connect_timeout=3,
        socket_timeout=3,
        retry_on_timeout=True,
        max_connections=20,
    )


@lru_cache
def get_sync_redis() -> redis.Redis | None:
    """Get a sync Redis client (for use in FastAPI sync dependencies).

    Returns ``None`` if Redis is not configured.
    """
    import redis as sync_redis

    url = _redis_url()
    if not url:
        return None
    return sync_redis.from_url(
        url,
        encoding="utf-8",
        decode_responses=True,
        socket_connect_timeout=3,
        socket_timeout=3,
        retry_on_timeout=True,
        max_connections=10,
    )


async def close_redis() -> None:
    """Close the async Redis connection pool (call on shutdown)."""
    client = get_redis()
    if client is not None:
        await client.close()
        get_redis.cache_clear()
        logger.info("Async Redis connection closed")


async def redis_ping() -> bool:
    """Check if Redis is reachable."""
    client = get_redis()
    if client is None:
        return False
    try:
        return await client.ping()
    except Exception:
        return False


async def check_idempotency_key(key: str, ttl: int = 300) -> bool:
    """Check if an idempotency key has already been processed.

    Returns ``True`` if the key is new (not yet processed),
    ``False`` if it was already seen (duplicate request).
    """
    client = get_redis()
    if client is None:
        return True
    result = await client.setnx(f"idempotency:{key}", "1")
    if result:
        await client.expire(f"idempotency:{key}", ttl)
        return True
    return False
