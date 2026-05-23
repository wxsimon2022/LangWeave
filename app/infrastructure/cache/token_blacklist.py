"""Token blacklisting and revocation via Redis.

When a user logs out or a token is revoked, the token's ``jti`` (UUID)
is stored in Redis with a TTL matching the token's remaining lifetime.

All authenticated requests check the blacklist before accepting the token.
Both async and sync versions are provided.
"""

from __future__ import annotations

from datetime import UTC, datetime

from jose import JWTError, jwt

from app.application.security import get_auth_settings
from app.infrastructure.cache import get_redis, get_sync_redis

BLACKLIST_PREFIX = "token:blacklist:"


def _get_token_expiry(token: str) -> int:
    """Get the remaining TTL of a JWT in seconds."""
    try:
        settings = get_auth_settings()
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],
            options={"verify_exp": True},
        )
        exp = payload.get("exp", 0)
        now = datetime.now(UTC).timestamp()
        return max(0, int(exp - now))
    except JWTError:
        return 0


def get_jti(token: str) -> str | None:
    """Extract the ``jti`` claim from a JWT without full verification."""
    try:
        payload = jwt.get_unverified_claims(token)
        return payload.get("jti")
    except JWTError:
        return None


# ---------------------------------------------------------------------------
# Async versions (for route handlers)
# ---------------------------------------------------------------------------

async def blacklist_token_async(token: str) -> bool:
    """Async: add a token's JTI to the Redis blacklist.

    Returns ``True`` if blacklisted, ``False`` if Redis is unavailable.
    """
    client = get_redis()
    if client is None:
        return False

    jti = get_jti(token)
    if not jti:
        return False

    ttl = _get_token_expiry(token)
    if ttl <= 0:
        return False

    await client.setex(f"{BLACKLIST_PREFIX}{jti}", ttl, "1")
    return True


async def is_token_blacklisted_async(token: str) -> bool:
    """Async: check if a token's JTI has been blacklisted."""
    client = get_redis()
    if client is None:
        return False

    jti = get_jti(token)
    if not jti:
        return False

    result = await client.get(f"{BLACKLIST_PREFIX}{jti}")
    return result is not None


# ---------------------------------------------------------------------------
# Sync versions (for FastAPI sync dependencies like get_current_user)
# ---------------------------------------------------------------------------

def blacklist_token_sync(token: str) -> bool:
    """Sync: add a token's JTI to the Redis blacklist."""
    client = get_sync_redis()
    if client is None:
        return False

    jti = get_jti(token)
    if not jti:
        return False

    ttl = _get_token_expiry(token)
    if ttl <= 0:
        return False

    client.setex(f"{BLACKLIST_PREFIX}{jti}", ttl, "1")
    return True


def is_token_blacklisted_sync(token: str) -> bool:
    """Sync: check if a token's JTI has been blacklisted."""
    client = get_sync_redis()
    if client is None:
        return False

    jti = get_jti(token)
    if not jti:
        return False

    result = client.get(f"{BLACKLIST_PREFIX}{jti}")
    return result is not None
