"""Daily Active User (DAU) statistics backed by Redis.

Design:
- Each user heartbeat triggers a PFADD to a daily HyperLogLog key.
- HyperLogLog uses ~12KB per key and provides ~0.81% error rate for
  cardinality estimation — perfect for DAU tracking.
- A Sorted Set stores historic DAU counts per day for charting.
- A Sorted Set tracks real-time concurrency (peak online) each day.

Redis keys:
  dau:{YYYY-MM-DD}           — HyperLogLog, user_id set (DAU count)
  dau:history                — Sorted Set, score=YYYYMMDD, member=count
  dau:peak:{YYYY-MM-DD}      — Sorted Set, score=timestamp, member=user_id
"""

from __future__ import annotations

import logging
import time
from datetime import UTC, date, datetime, timedelta

from app.infrastructure.cache import get_redis, get_sync_redis

logger = logging.getLogger(__name__)

DAU_PREFIX = "dau"
DAU_HISTORY_KEY = f"{DAU_PREFIX}:history"
DAU_PEAK_PREFIX = f"{DAU_PREFIX}:peak"

# Keep peak data for 90 days
PEAK_TTL = 90 * 86400

# Keep HyperLogLog keys for 90 days
DAU_TTL = 90 * 86400


def _today_key() -> str:
    return f"{DAU_PREFIX}:{date.today().isoformat()}"


def _date_key(d: date) -> str:
    return f"{DAU_PREFIX}:{d.isoformat()}"


def _peak_key(d: date) -> str:
    return f"{DAU_PEAK_PREFIX}:{d.isoformat()}"


def _ymd(d: date) -> int:
    """Convert date to YYYYMMDD integer for Sorted Set score."""
    return d.year * 10000 + d.month * 100 + d.day


# ---------------------------------------------------------------------------
# Async
# ---------------------------------------------------------------------------


async def record_dau_async(user_id: int) -> None:
    """Record a user activity for today's DAU.

    Should be called once per user session (e.g. on heartbeat or login).
    Uses HyperLogLog for memory-efficient deduplication.
    """
    client = get_redis()
    if client is None:
        return

    today = date.today()
    dau_key = _date_key(today)

    pipe = client.pipeline()
    pipe.pfadd(dau_key, str(user_id))
    pipe.expire(dau_key, DAU_TTL)
    await pipe.execute()

    # Also record in peak concurrency set (for max concurrent today)
    peak_key = _peak_key(today)
    now_ts = int(time.time())
    pipe = client.pipeline()
    pipe.zadd(peak_key, {str(user_id): now_ts})
    pipe.expire(peak_key, PEAK_TTL)
    await pipe.execute()


async def snapshot_dau_async() -> None:
    """Take a snapshot of today's DAU count and store in history.

    Call periodically (e.g. every hour) or on demand.
    """
    client = get_redis()
    if client is None:
        return

    today = date.today()
    dau_key = _date_key(today)
    count = await client.pfcount(dau_key)
    if count > 0:
        ymd = _ymd(today)
        await client.zadd(DAU_HISTORY_KEY, {str(count): ymd})


async def get_dau_history_async(
    days: int = 30,
) -> list[dict]:
    """Get DAU history for the last N days.

    Returns a list of {date, dau} sorted by date ascending.
    """
    client = get_redis()
    if client is None:
        return []

    today = date.today()
    start_date = today - timedelta(days=days - 1)

    # Get history from Sorted Set in the range
    start_ymd = _ymd(start_date)
    end_ymd = _ymd(today)

    # Get stored history entries
    results = await client.zrangebyscore(
        DAU_HISTORY_KEY, start_ymd, end_ymd, withscores=True,
    )
    history = {int(score): int(member) for member, score in results}

    # Get today's live count (might not be snapshotted yet)
    today_dau = await client.pfcount(_date_key(today))

    # Build complete list
    dau_data = []
    for i in range(days):
        d = start_date + timedelta(days=i)
        ymd = _ymd(d)
        if d == today:
            count = today_dau
        else:
            count = history.get(ymd, 0)
        dau_data.append({
            "date": d.isoformat(),
            "dau": count,
        })
    return dau_data


async def get_today_dau_async() -> int:
    """Get today's DAU count."""
    client = get_redis()
    if client is None:
        return 0
    return await client.pfcount(_date_key(date.today())) or 0


async def get_peak_concurrent_async() -> int:
    """Get today's peak concurrent online count.

    Counts unique user IDs in the peak set within the last N seconds.
    """
    client = get_redis()
    if client is None:
        return 0

    today = date.today()
    peak_key = _peak_key(today)
    now = int(time.time())

    # Count unique users active in the last 90 seconds
    cutoff = now - 90
    count = await client.zcount(peak_key, cutoff, "+inf")
    return count or 0


async def get_dau_summary_async(days: int = 7) -> dict:
    """Get a summary: daily DAU for the last N days + today's peak concurrent."""
    dau_history = await get_dau_history_async(days)
    peak = await get_peak_concurrent_async()
    today_dau = await get_today_dau_async()
    total_unique = sum(item["dau"] for item in dau_history)

    return {
        "today_dau": today_dau,
        "peak_concurrent": peak,
        "total_unique": total_unique,
        "daily": dau_history,
    }


# ---------------------------------------------------------------------------
# Sync versions (for admin routes if needed)
# ---------------------------------------------------------------------------


def get_dau_history_sync(days: int = 30) -> list[dict]:
    """Sync: get DAU history."""
    client = get_sync_redis()
    if client is None:
        return []

    today = date.today()
    start_date = today - timedelta(days=days - 1)
    start_ymd = _ymd(start_date)
    end_ymd = _ymd(today)

    results = client.zrangebyscore(DAU_HISTORY_KEY, start_ymd, end_ymd, withscores=True)
    history = {int(score): int(member) for member, score in results}
    today_dau = client.pfcount(_date_key(today)) or 0

    dau_data = []
    for i in range(days):
        d = start_date + timedelta(days=i)
        ymd = _ymd(d)
        count = today_dau if d == today else history.get(ymd, 0)
        dau_data.append({"date": d.isoformat(), "dau": count})
    return dau_data


def get_today_dau_sync() -> int:
    client = get_sync_redis()
    if client is None:
        return 0
    return client.pfcount(_date_key(date.today())) or 0


def get_dau_summary_sync(days: int = 7) -> dict:
    dau_history = get_dau_history_sync(days)
    today_dau = get_today_dau_sync()
    total_unique = sum(item["dau"] for item in dau_history)
    return {
        "today_dau": today_dau,
        "daily": dau_history,
        "total_unique": total_unique,
    }
