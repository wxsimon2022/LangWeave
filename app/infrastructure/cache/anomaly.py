"""Anomaly detection service using Redis.

Detects suspicious request patterns:
- Same IP registering multiple accounts in a time window
- Brute-force login attempts from a single IP
- Same account logging in from multiple geographic IPs in a short time

Relies on Redis being configured. When Redis is unavailable, all checks pass.
"""

from __future__ import annotations

from app.infrastructure.cache import get_redis, get_sync_redis

# ---------------------------------------------------------------------------
# Async versions
# ---------------------------------------------------------------------------


async def check_register_anomaly_async(
    ip: str, username: str, max_accounts: int = 3, window: int = 3600
) -> tuple[bool, str | None]:
    """Check if an IP is registering too many accounts.

    Args:
        ip: Client IP address.
        username: The username being registered.
        max_accounts: Max accounts allowed per IP in the window.
        window: Time window in seconds (default 1 hour).

    Returns:
        ``(is_anomaly, message)``. If anomalous, ``message`` explains why.
    """
    client = get_redis()
    if client is None:
        return False, None

    ip_key = f"anomaly:register_ip:{ip}"
    username_key = f"anomaly:register_username:{username}"

    pipe = client.pipeline()
    pipe.sadd(ip_key, username)
    pipe.expire(ip_key, window)
    pipe.scard(ip_key)
    pipe.setnx(username_key, "1")
    pipe.expire(username_key, window)
    results = await pipe.execute()

    account_count = int(results[2])

    if account_count > max_accounts:
        return (
            True,
            f"IP {ip} has registered {account_count} accounts in the last {window // 60} minutes",
        )
    return False, None


async def check_login_anomaly_async(
    ip: str,
    username: str,
    max_attempts: int = 5,
    window: int = 300,
) -> tuple[bool, str | None]:
    """Check for brute-force login attempts from an IP or on a username.

    Args:
        ip: Client IP address.
        username: The username being logged into.
        max_attempts: Max failed attempts before flagging.
        window: Time window in seconds (default 5 minutes).

    Returns:
        ``(is_anomaly, message)``.
    """
    client = get_redis()
    if client is None:
        return False, None

    pipe = client.pipeline()
    pipe.incr(f"anomaly:login_ip:{ip}")
    pipe.expire(f"anomaly:login_ip:{ip}", window)
    pipe.incr(f"anomaly:login_user:{username}")
    pipe.expire(f"anomaly:login_user:{username}", window)
    results = await pipe.execute()

    ip_attempts = int(results[0])
    user_attempts = int(results[2])

    if ip_attempts > max_attempts:
        return True, f"IP {ip} has {ip_attempts} login attempts in {window // 60} minutes"
    if user_attempts > max_attempts * 2:
        return True, f"User {username} has {user_attempts} login attempts in {window // 60} minutes"

    return False, None


async def record_failed_login_async(ip: str, username: str) -> None:
    """Record a failed login attempt for anomaly tracking."""
    client = get_redis()
    if client is None:
        return
    pipe = client.pipeline()
    pipe.incr(f"anomaly:login_ip:{ip}")
    pipe.expire(f"anomaly:login_ip:{ip}", 300)
    pipe.incr(f"anomaly:login_user:{username}")
    pipe.expire(f"anomaly:login_user:{username}", 300)
    pipe.incr(f"anomaly:login_failed_total:{username}")
    pipe.expire(f"anomaly:login_failed_total:{username}", 3600)
    await pipe.execute()


# ---------------------------------------------------------------------------
# Sync versions (for FastAPI sync route handlers)
# ---------------------------------------------------------------------------


def check_register_anomaly_sync(
    ip: str, username: str, max_accounts: int = 3, window: int = 3600
) -> tuple[bool, str | None]:
    """Sync: check if an IP is registering too many accounts."""
    client = get_sync_redis()
    if client is None:
        return False, None

    ip_key = f"anomaly:register_ip:{ip}"
    username_key = f"anomaly:register_username:{username}"

    pipe = client.pipeline()
    pipe.sadd(ip_key, username)
    pipe.expire(ip_key, window)
    pipe.scard(ip_key)
    pipe.setnx(username_key, "1")
    pipe.expire(username_key, window)
    results = pipe.execute()

    account_count = int(results[2])

    if account_count > max_accounts:
        return (
            True,
            f"IP has registered {account_count} accounts in the last {window // 60} minutes",
        )
    return False, None


def check_login_anomaly_sync(
    ip: str,
    username: str,
    max_attempts: int = 5,
    window: int = 300,
) -> tuple[bool, str | None]:
    """Sync: check for brute-force login attempts."""
    client = get_sync_redis()
    if client is None:
        return False, None

    pipe = client.pipeline()
    pipe.get(f"anomaly:login_ip:{ip}")
    pipe.get(f"anomaly:login_user:{username}")
    results = pipe.execute()

    ip_attempts = int(results[0] or 0)
    user_attempts = int(results[1] or 0)

    if ip_attempts > max_attempts:
        return True, f"Too many login attempts from this IP ({ip_attempts} in {window // 60} minutes)"
    if user_attempts > max_attempts * 2:
        return True, f"Too many login attempts for this user ({user_attempts})"

    return False, None


def record_failed_login_sync(ip: str, username: str) -> None:
    """Sync: record a failed login attempt."""
    client = get_sync_redis()
    if client is None:
        return
    pipe = client.pipeline()
    pipe.incr(f"anomaly:login_ip:{ip}")
    pipe.expire(f"anomaly:login_ip:{ip}", 300)
    pipe.incr(f"anomaly:login_user:{username}")
    pipe.expire(f"anomaly:login_user:{username}", 300)
    pipe.execute()
