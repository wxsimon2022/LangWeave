"""Security middleware: Redis-based rate limiting and HTTP response headers.

If Redis is not configured, the middleware falls back to basic in-memory
rate limiting so the application still works without Redis.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.infrastructure.cache import get_redis, is_redis_available

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# In-memory Token Bucket (fallback when Redis is unavailable)
# ---------------------------------------------------------------------------

class _MemoryTokenBucket:
    """Simple in-memory token bucket for per-IP rate limiting (fallback)."""

    __slots__ = ("capacity", "refill_rate", "_tokens", "_last_refill")

    def __init__(self, capacity: int, refill_rate: float) -> None:
        self.capacity = capacity
        self.refill_rate = refill_rate
        self._tokens = float(capacity)
        self._last_refill = time.monotonic()

    def consume(self) -> bool:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self.capacity, self._tokens + elapsed * self.refill_rate)
        self._last_refill = now
        if self._tokens >= 1.0:
            self._tokens -= 1.0
            return True
        return False


# ---------------------------------------------------------------------------
# Rate Limit Middleware
# ---------------------------------------------------------------------------

class RateLimitExceeded(Exception):
    """Raised when a client exceeds the rate limit."""


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate-limit requests per IP address.

    **Redis mode** (recommended):
    - Uses Redis ``INCR`` + ``EXPIRE`` for sliding-window rate counting.
    - Works across multiple workers/processes.
    - Requires ``LANGWEAVE_REDIS_URL`` env var.

    **Memory fallback** (when Redis is unavailable):
    - Per-process in-memory token bucket.
    - Limits reset on process restart; does not work across workers.

    Default limits:
    - General endpoints: 60 req/min per IP
    - Login: 10 req/min per IP
    - Register: 5 req/min per IP
    """

    def __init__(
        self,
        app: Any,
        *,
        default_capacity: int = 60,
        default_window: int = 60,
        strict_limits: dict[str, tuple[int, int]] | None = None,
        exclude_paths: set[str] | None = None,
    ) -> None:
        super().__init__(app)
        self._default_capacity = default_capacity
        self._default_window = default_window
        self._strict: dict[str, tuple[int, int]] = strict_limits or {
            "/api/v1/auth/login": (10, 60),     # 10 requests per 60s
            "/api/v1/auth/register": (5, 60),    # 5 requests per 60s
        }
        self._exclude: set[str] = exclude_paths or set()
        # Memory fallback buckets
        self._memory_buckets: dict[str, _MemoryTokenBucket] = {}
        self._use_redis = is_redis_available()

    async def _check_rate_redis(self, key: str, limit: int, window: int) -> tuple[bool, int]:
        """Check rate limit via Redis sliding window.

        Returns (allowed, current_count).
        """
        client = get_redis()
        if client is None:
            return True, 0

        try:
            pipe = client.pipeline()
            pipe.incr(key)
            pipe.expire(key, window)
            count, _ = await pipe.execute()
            count = int(count)
            if count == 1:
                # First request — initialize TTL
                await client.expire(key, window)
            return count <= limit, count
        except Exception as exc:
            logger.warning("Redis rate check failed (falling through): %s", exc)
            return True, 0

    async def _check_rate_memory(self, key: str, limit: int, window: int) -> tuple[bool, int]:
        """Check rate limit via in-memory token bucket (fallback)."""
        if key not in self._memory_buckets:
            # Convert (limit, window) to token bucket parameters:
            # capacity = limit, refill_rate = limit / window (tokens per second)
            refill = limit / max(window, 1)
            self._memory_buckets[key] = _MemoryTokenBucket(limit, refill)
        allowed = self._memory_buckets[key].consume()
        remaining = max(0, int(self._memory_buckets[key]._tokens))
        return allowed, remaining

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        path = request.url.path

        # Skip excluded paths
        if path in self._exclude:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"

        # Determine rate limits for this path
        if path in self._strict:
            limit, window = self._strict[path]
        else:
            limit, window = self._default_capacity, self._default_window

        # Rate key: IP-based
        rate_key = f"ratelimit:{client_ip}:{path.replace('/', '_')}"

        if self._use_redis:
            allowed, count = await self._check_rate_redis(rate_key, limit, window)
        else:
            allowed, count = await self._check_rate_memory(rate_key, limit, window)

        if not allowed:
            return Response(
                content='{"detail":"Too many requests. Please slow down."}',
                status_code=429,
                media_type="application/json",
                headers={
                    "Retry-After": str(window),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, limit - count))
        return response


# ---------------------------------------------------------------------------
# Security Headers Middleware
# ---------------------------------------------------------------------------

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security-related HTTP headers to every response.

    Implements recommended headers from OWASP Secure Headers Project.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self' data:; "
            "connect-src 'self' https://api.github.com; "
            "frame-ancestors 'none';"
        )
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), interest-cohort=()"
        )

        return response
