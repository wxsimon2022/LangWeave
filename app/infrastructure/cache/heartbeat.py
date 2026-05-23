"""User heartbeat (online status) service backed by Redis.

Design:
- Each active user sends a heartbeat every 30 seconds.
- The heartbeat updates a Redis Sorted Set with score = current timestamp.
- Users whose last heartbeat is older than HEARTBEAT_TTL seconds are considered offline.
- Admin API queries the Sorted Set to get the online user list.

Redis keys:
  heartbeat:users  — Sorted Set {user_id -> last_heartbeat_timestamp}
  heartbeat:users:{user_id}  — String, JSON with user info {username, ip, user_agent}
"""

from __future__ import annotations

import json
import logging
import time

from app.infrastructure.cache import get_redis, get_sync_redis

logger = logging.getLogger(__name__)

HEARTBEAT_PREFIX = "heartbeat:users"
HEARTBEAT_TTL = 90  # seconds — mark offline if no heartbeat for 90s
HEARTBEAT_INTERVAL = 30  # seconds — client should ping every 30s


# ---------------------------------------------------------------------------
# Async (for route handlers)
# ---------------------------------------------------------------------------


async def record_heartbeat_async(
    user_id: int,
    username: str,
    ip: str = "",
    user_agent: str = "",
) -> None:
    """Record a user heartbeat in Redis.

    Updates both the sorted set (for online query) and a user info hash.
    """
    client = get_redis()
    if client is None:
        logger.warning("Redis not available — heartbeat not recorded")
        return

    now = time.time()
    pipe = client.pipeline()

    # Sorted Set: member=user_id, score=timestamp
    pipe.zadd(HEARTBEAT_PREFIX, {str(user_id): now})

    # String: store user info with TTL
    info = json.dumps({
        "id": user_id,
        "username": username,
        "ip": ip,
        "user_agent": user_agent,
        "last_seen": now,
    })
    pipe.setex(f"{HEARTBEAT_PREFIX}:{user_id}", HEARTBEAT_TTL, info)

    # Maintain Sorted Set TTL — remove stale entries
    pipe.zremrangebyscore(HEARTBEAT_PREFIX, "-inf", now - HEARTBEAT_TTL)

    await pipe.execute()
    logger.debug("Heartbeat recorded for user %s (id=%d)", username, user_id)


async def get_online_users_async() -> list[dict]:
    """Get all currently online users from Redis.

    Returns a list of dicts with keys: id, username, ip, user_agent, last_seen.
    """
    client = get_redis()
    if client is None:
        return []

    now = time.time()
    cutoff = now - HEARTBEAT_TTL

    # Clean stale entries first
    await client.zremrangebyscore(HEARTBEAT_PREFIX, "-inf", cutoff)

    # Get active user IDs
    user_ids = await client.zrangebyscore(HEARTBEAT_PREFIX, cutoff, "+inf")
    if not user_ids:
        return []

    # Fetch user info for each
    users = []
    for uid in user_ids:
        data = await client.get(f"{HEARTBEAT_PREFIX}:{uid}")
        if data:
            try:
                users.append(json.loads(data))
            except json.JSONDecodeError:
                continue

    # Sort by last_seen descending
    users.sort(key=lambda u: u.get("last_seen", 0), reverse=True)
    logger.debug("get_online_users: found %d online users", len(users))
    return users


async def get_online_count_async() -> int:
    """Get the count of currently online users."""
    client = get_redis()
    if client is None:
        return 0
    now = time.time()
    cutoff = now - HEARTBEAT_TTL
    await client.zremrangebyscore(HEARTBEAT_PREFIX, "-inf", cutoff)
    return await client.zcount(HEARTBEAT_PREFIX, cutoff, "+inf")


async def is_user_online_async(user_id: int) -> bool:
    """Check if a specific user is online."""
    client = get_redis()
    if client is None:
        return False
    # Check if the user info key still exists (auto-expires after TTL)
    exists = await client.exists(f"{HEARTBEAT_PREFIX}:{user_id}")
    return bool(exists)


# ---------------------------------------------------------------------------
# Sync (for FastAPI sync dependencies / admin routes)
# ---------------------------------------------------------------------------


def get_online_users_sync() -> list[dict]:
    """Sync: get all currently online users."""
    client = get_sync_redis()
    if client is None:
        return []

    now = time.time()
    cutoff = now - HEARTBEAT_TTL

    client.zremrangebyscore(HEARTBEAT_PREFIX, "-inf", cutoff)
    user_ids = client.zrangebyscore(HEARTBEAT_PREFIX, cutoff, "+inf")
    if not user_ids:
        return []

    users = []
    for uid in user_ids:
        data = client.get(f"{HEARTBEAT_PREFIX}:{uid}")
        if data:
            try:
                users.append(json.loads(data))
            except json.JSONDecodeError:
                continue

    users.sort(key=lambda u: u.get("last_seen", 0), reverse=True)
    return users


def get_online_count_sync() -> int:
    """Sync: get the count of currently online users."""
    client = get_sync_redis()
    if client is None:
        return 0
    now = time.time()
    cutoff = now - HEARTBEAT_TTL
    client.zremrangebyscore(HEARTBEAT_PREFIX, "-inf", cutoff)
    return client.zcount(HEARTBEAT_PREFIX, cutoff, "+inf") or 0
