"""Password hashing and JWT helpers.

Security hardening:
- JWT includes: sub, iat, exp, jti (unique token ID)
- Access token: expires in 2 hours (configurable)
- Refresh token: expires in 30 days, used to get new access tokens
- PBKDF2-HMAC-SHA256 with 390k iterations
- HMAC-SHA256 request signing for API integrity verification
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache

from jose import JWTError, jwt

from langweave.config import load_dotenv
from app.constants import JWT_ALGORITHM, PBKDF2_ITERATIONS, DEFAULT_JWT_EXPIRE_MINUTES


@dataclass(frozen=True)
class AuthSettings:
    """JWT-related runtime settings."""

    jwt_secret: str
    access_token_expire_minutes: int = DEFAULT_JWT_EXPIRE_MINUTES
    refresh_token_expire_minutes: int = 60 * 24 * 30  # 30 days
    api_signing_secret: str = ""
    api_signing_enabled: bool = False


@lru_cache
def get_auth_settings() -> AuthSettings:
    """Load auth settings from env with fallback chain."""
    load_dotenv()
    secret = os.environ.get("LANGWEAVE_JWT_SECRET") or os.environ.get(
        "JWT_SECRET"
    ) or "change-this-dev-secret"
    expire = int(
        os.environ.get("LANGWEAVE_JWT_EXPIRE_MINUTES")
        or os.environ.get("JWT_EXPIRE_MINUTES")
        or DEFAULT_JWT_EXPIRE_MINUTES
    )
    api_secret = os.environ.get("LANGWEAVE_API_SIGNING_SECRET") or ""
    return AuthSettings(
        jwt_secret=secret,
        access_token_expire_minutes=expire,
        api_signing_secret=api_secret,
        api_signing_enabled=bool(api_secret),
    )


def _pbkdf2_hash(password: str, salt: bytes, iterations: int) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)


def hash_password(password: str) -> str:
    """Hash a password using PBKDF2-HMAC-SHA256 with a random salt."""
    salt = os.urandom(16)
    digest = _pbkdf2_hash(password, salt, PBKDF2_ITERATIONS)
    salt_b64 = base64.b64encode(salt).decode("utf-8")
    digest_b64 = base64.b64encode(digest).decode("utf-8")
    return f"{PBKDF2_ITERATIONS}${salt_b64}${digest_b64}"


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against the stored PBKDF2 hash."""
    try:
        iterations_text, salt_b64, digest_b64 = password_hash.split("$", maxsplit=2)
        salt = base64.b64decode(salt_b64.encode("utf-8"))
        expected = base64.b64decode(digest_b64.encode("utf-8"))
        actual = _pbkdf2_hash(password, salt, int(iterations_text))
        return actual == expected
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: int, extra_claims: dict | None = None) -> str:
    """Create a signed JWT access token for the given user.

    The token includes:
    - ``sub``: user ID
    - ``iat``: issued at timestamp
    - ``exp``: expiration timestamp (default 2 hours, configurable)
    - ``jti``: unique token ID (UUID v4) for revocation support
    - ``type``: ``"access"``
    """
    settings = get_auth_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
        "jti": str(uuid.uuid4()),
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.jwt_secret, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    """Create a signed JWT refresh token.

    The token includes:
    - ``sub``: user ID
    - ``iat``: issued at timestamp
    - ``exp``: expiration timestamp (30 days)
    - ``jti``: unique token ID
    - ``type``: ``"refresh"``
    """
    settings = get_auth_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.refresh_token_expire_minutes),
        "jti": str(uuid.uuid4()),
        "type": "refresh",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> int:
    """Decode a signed JWT access token and return the user ID.

    Validates:
    - Signature
    - Expiration
    - Token type is ``"access"``
    """
    settings = get_auth_settings()
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[JWT_ALGORITHM])
    subject = payload.get("sub")
    if subject is None:
        msg = "Token subject is missing"
        raise JWTError(msg)
    if payload.get("type") != "access":
        msg = "Token is not an access token"
        raise JWTError(msg)
    return int(subject)


def decode_refresh_token(token: str) -> int:
    """Decode a signed JWT refresh token and return the user ID.

    Validates:
    - Signature
    - Expiration
    - Token type is ``"refresh"``
    """
    settings = get_auth_settings()
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[JWT_ALGORITHM])
    subject = payload.get("sub")
    if subject is None:
        msg = "Refresh token subject is missing"
        raise JWTError(msg)
    if payload.get("type") != "refresh":
        msg = "Token is not a refresh token"
        raise JWTError(msg)
    return int(subject)


# ---------------------------------------------------------------------------
# HMAC-SHA256 API request signing (optional extra layer)
# ---------------------------------------------------------------------------
# The frontend signs the request body + timestamp with a shared secret.
# The backend verifies the signature to ensure request integrity.
# Enable by setting LANGWEAVE_API_SIGNING_SECRET in .env.prod


def sign_request(body: str, timestamp: int, secret: str | None = None) -> str:
    """Create an HMAC-SHA256 signature for a request body + timestamp.

    Args:
        body: The request body as a JSON string.
        timestamp: Unix timestamp (seconds) sent in the ``X-Timestamp`` header.
        secret: The shared signing secret. Defaults to the configured secret.

    Returns:
        Base64-encoded HMAC-SHA256 signature.
    """
    if secret is None:
        secret = get_auth_settings().api_signing_secret
    message = f"{timestamp}.{body}"
    digest = hmac.new(
        secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256
    ).digest()
    return base64.b64encode(digest).decode("utf-8")


def verify_request_signature(
    body: str,
    timestamp: int,
    signature: str,
    max_age_seconds: int = 300,
    secret: str | None = None,
) -> bool:
    """Verify an HMAC-SHA256 request signature.

    Checks:
    1. Timestamp is within ``max_age_seconds`` of now (prevents replay attacks).
    2. Computed HMAC matches the provided signature.

    Args:
        body: The request body as a JSON string.
        timestamp: Unix timestamp from the ``X-Timestamp`` header.
        signature: Base64-encoded HMAC from the ``X-Signature`` header.
        max_age_seconds: Max allowed age of the timestamp (default 5 min).
        secret: The shared signing secret.

    Returns:
        ``True`` if the signature is valid, ``False`` otherwise.
    """
    # Check timestamp freshness
    now = time.time()
    if abs(now - timestamp) > max_age_seconds:
        return False

    settings = get_auth_settings()
    if secret is None:
        secret = settings.api_signing_secret
    if not secret:
        return True  # signing not configured — skip verification

    expected = sign_request(body, timestamp, secret)
    return hmac.compare_digest(expected, signature)
