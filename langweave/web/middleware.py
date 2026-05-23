"""Security middleware for rate limiting and HTTP response headers."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


# ---------------------------------------------------------------------------
# Rate Limiting (in-memory token bucket)
# ---------------------------------------------------------------------------

class RateLimitExceeded(Exception):
    """Raised when a client exceeds the rate limit."""


class _TokenBucket:
    """Simple in-memory token bucket for per-IP rate limiting."""

    __slots__ = ("capacity", "refill_rate", "_tokens", "_last_refill")

    def __init__(self, capacity: int, refill_rate: float) -> None:
        self.capacity = capacity
        self.refill_rate = refill_rate  # tokens per second
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


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate-limit requests per IP address using an in-memory token bucket.

    Default: 60 requests per minute per IP (burst up to 60).
    Login/register endpoints get stricter limits.

    Usage:
        app.add_middleware(RateLimitMiddleware)
    """

    def __init__(
        self,
        app: Any,
        *,
        default_capacity: int = 60,
        default_refill: float = 1.0,  # 1 token/sec ≈ 60 req/min
        strict_paths: dict[str, tuple[int, float]] | None = None,
        exclude_paths: set[str] | None = None,
    ) -> None:
        super().__init__(app)
        self._default_capacity = default_capacity
        self._default_refill = default_refill
        self._buckets: dict[str, _TokenBucket] = {}
        self._strict: dict[str, tuple[int, float]] = strict_paths or {
            "/api/v1/auth/login": (10, 0.17),     # 10 burst, ~10 req/min
            "/api/v1/auth/register": (5, 0.08),    # 5 burst, ~5 req/min
        }
        self._exclude: set[str] = exclude_paths or set()

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
            capacity, refill = self._strict[path]
        else:
            capacity, refill = self._default_capacity, self._default_refill

        # Get or create bucket for this IP
        bucket_key = f"{client_ip}:{path}"
        if bucket_key not in self._buckets:
            self._buckets[bucket_key] = _TokenBucket(capacity, refill)

        if not self._buckets[bucket_key].consume():
            return Response(
                content='{"detail":"Rate limit exceeded. Please slow down."}',
                status_code=429,
                media_type="application/json",
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Limit": str(capacity),
                },
            )

        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(capacity)
        response.headers["X-RateLimit-Remaining"] = str(
            max(0, int(self._buckets[bucket_key]._tokens))
        )

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

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Enable browser XSS filter (legacy, but harmless)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # HSTS (force HTTPS) — only in production
        # response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Content Security Policy — restrict resource loading
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self' data:; "
            "connect-src 'self' https://api.github.com; "
            "frame-ancestors 'none';"
        )

        # Permissions Policy (restrict browser features)
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), interest-cohort=()"
        )

        return response
