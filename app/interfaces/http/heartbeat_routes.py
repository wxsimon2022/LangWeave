"""Heartbeat HTTP routes — client sends periodic pings to indicate online status."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request

from app.infrastructure.cache.dau import record_dau_async, snapshot_dau_async
from app.infrastructure.cache.heartbeat import record_heartbeat_async
from app.interfaces.http.deps import CurrentUser
from langweave.web.response import ApiResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/heartbeat", tags=["heartbeat"])

# Snapshot DAU every N heartbeats (approx every 30 * 120 = 3600s = 1h)
_DAU_SNAPSHOT_INTERVAL = 120
_dau_snapshot_counter = 0


@router.post(
    "/ping",
    summary="用户心跳上报",
    description="客户端每 30 秒调用一次，更新用户在线状态。超时 90 秒无心跳视为离线。",
)
async def heartbeat_ping(
    user: CurrentUser,
    request: Request,
) -> ApiResponse[dict]:
    client_ip = request.client.host if request.client else ""
    user_agent = request.headers.get("User-Agent", "")

    logger.info(
        "Heartbeat from user %s (id=%d, ip=%s)",
        user.username, user.id, client_ip,
    )

    await record_heartbeat_async(
        user_id=user.id,
        username=user.username,
        ip=client_ip,
        user_agent=user_agent,
    )

    # Record DAU — HyperLogLog daily active user
    await record_dau_async(user_id=user.id)

    # Periodically snapshot DAU to history
    global _dau_snapshot_counter
    _dau_snapshot_counter += 1
    if _dau_snapshot_counter >= _DAU_SNAPSHOT_INTERVAL:
        _dau_snapshot_counter = 0
        await snapshot_dau_async()

    return ApiResponse.ok({"status": "ok"})
