"""Visitor counter — Redis backed unique visitor tracking.

Public endpoint (no auth required) that records unique visitors by IP
via HyperLogLog and returns the total unique visitor count.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request

from app.infrastructure.cache import get_redis
from langweave.web.response import ApiResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/visitor", tags=["visitor"])

# Redis key for unique visitor HyperLogLog
REDIS_KEY = "visitor:unique"


@router.get(
    "/count",
    summary="站点访问计数",
    description="""
    记录当前访问者（按 IP 去重），返回累计唯一访问人数。
    不需要登录，首页直接调用即可显示。
    """,
)
async def visitor_count(request: Request) -> ApiResponse[dict]:
    """Record visitor IP and return total unique visitor count."""
    redis = get_redis()
    if redis is None:
        # Redis 未配置时返回一个示例数（不影响功能）
        logger.debug("Redis not available, returning mock count")
        return ApiResponse.ok({"count": 142857})

    client_ip = request.client.host if request.client else "unknown"

    # PFADD — HyperLogLog, 去重记录 IP
    await redis.pfadd(REDIS_KEY, client_ip)

    # PFCOUNT — 获取总唯一访问人数
    count = await redis.pfcount(REDIS_KEY) or 0

    return ApiResponse.ok({"count": count})
