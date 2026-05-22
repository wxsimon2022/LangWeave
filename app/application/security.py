"""Password hashing and JWT helpers."""

from __future__ import annotations

import base64
import hashlib
import os
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


@lru_cache
def get_auth_settings() -> AuthSettings:
    """Load auth settings from env with fallback chain."""
    load_dotenv()
    secret = os.environ.get("LANGWEAVE_JWT_SECRET") or os.environ.get("JWT_SECRET") or "change-this-dev-secret"
    expire = int(
        os.environ.get("LANGWEAVE_JWT_EXPIRE_MINUTES")
        or os.environ.get("JWT_EXPIRE_MINUTES")
        or DEFAULT_JWT_EXPIRE_MINUTES
    )
    return AuthSettings(jwt_secret=secret, access_token_expire_minutes=expire)


def _pbkdf2_hash(password: str, salt: bytes, iterations: int) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)


def hash_password(password: str) -> str:
    """Hash a password using PBKDF2-HMAC."""
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


def create_access_token(user_id: int) -> str:
    """Create a signed JWT for the given user."""
    settings = get_auth_settings()
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode({"sub": str(user_id), "exp": expires_at}, settings.jwt_secret, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> int:
    """Decode a signed JWT and return the user id."""
    settings = get_auth_settings()
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[JWT_ALGORITHM])
    subject = payload.get("sub")
    if subject is None:
        msg = "Token subject is missing"
        raise JWTError(msg)
    return int(subject)
