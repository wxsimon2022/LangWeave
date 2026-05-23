"""Active session tracking — single-device login enforcement.

When a user logs in, the new token's ``jti`` is stored in Redis as the
"active" session for that user.  Every authenticated request checks that
the presented token's ``jti`` matches the stored active session.  If they
differ, the token is considered "kicked" and the user must log in again.

Key pattern: ``session:active:{user_id}`` → ``jti``  (no TTL — lives as
long as the user has an active session; cleared on manual logout).
"""

from __future__ import annotations

from app.constants import REDIS_KEY_PREFIX
from app.infrastructure.cache import get_redis, get_sync_redis

SESSION_PREFIX = f"{REDIS_KEY_PREFIX}session:active:"


# ---------------------------------------------------------------------------
# Async (for route handlers)
# ---------------------------------------------------------------------------

async def set_active_session_async(user_id: int, jti: str) -> bool:
    """Store ``jti`` as the active session for ``user_id``.

    Returns ``True`` if stored, ``False`` if Redis is unavailable.
    """
    client = get_redis()
    if client is None:
        return False
    key = f"{SESSION_PREFIX}{user_id}"
    await client.set(key, jti)
    return True


async def get_active_session_async(user_id: int) -> str | None:
    """Return the active ``jti`` for ``user_id``, or ``None``."""
    client = get_redis()
    if client is None:
        return None
    key = f"{SESSION_PREFIX}{user_id}"
    result = await client.get(key)
    return result


async def clear_active_session_async(user_id: int) -> bool:
    """Remove the active session record for ``user_id``.

    Returns ``True`` if cleared, ``False`` if Redis is unavailable.
    """
    client = get_redis()
    if client is None:
        return False
    key = f"{SESSION_PREFIX}{user_id}"
    await client.delete(key)
    return True


# ---------------------------------------------------------------------------
# Sync (for FastAPI sync dependencies like get_current_user)
# ---------------------------------------------------------------------------

def get_active_session_sync(user_id: int) -> str | None:
    """Sync: return the active ``jti`` for ``user_id``, or ``None``."""
    client = get_sync_redis()
    if client is None:
        return None
    key = f"{SESSION_PREFIX}{user_id}"
    result = client.get(key)
    return result


def clear_active_session_sync(user_id: int) -> bool:
    """Sync: remove the active session record for ``user_id``."""
    client = get_sync_redis()
    if client is None:
        return False
    key = f"{SESSION_PREFIX}{user_id}"
    client.delete(key)
    return True


def set_active_session_sync(user_id: int, jti: str) -> bool:
    """Sync: store ``jti`` as the active session for ``user_id``."""
    client = get_sync_redis()
    if client is None:
        return False
    key = f"{SESSION_PREFIX}{user_id}"
    client.set(key, jti)
    return True
