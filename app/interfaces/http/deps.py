"""FastAPI dependencies for business routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.application.security import decode_access_token, get_auth_settings, verify_request_signature
from app.application.services.auth import AuthService
from app.application.services.emotional_chat import EmotionalChatService
from app.application.services.intent import IntentService
from app.application.services.session import SessionService
from app.infrastructure.persistence.database import get_db_session
from app.infrastructure.persistence.models import User
from langweave.registry import AgentRegistry
from langweave.web.deps import get_registry

bearer_scheme = HTTPBearer(auto_error=False)


def get_intent_service(
    registry: Annotated[AgentRegistry, Depends(get_registry)],
) -> IntentService:
    return IntentService(registry)


def get_session_service(
    registry: Annotated[AgentRegistry, Depends(get_registry)],
) -> SessionService:
    return SessionService(registry)


def get_auth_service(
    db: Annotated[Session, Depends(get_db_session)],
) -> AuthService:
    return AuthService(db)


def get_emotional_chat_service(
    db: Annotated[Session, Depends(get_db_session)],
    registry: Annotated[AgentRegistry, Depends(get_registry)],
) -> EmotionalChatService:
    return EmotionalChatService(db, registry)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )
    try:
        user_id = decode_access_token(credentials.credentials)
        return auth_service.get_user(user_id)
    except (JWTError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc


def get_current_admin_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user


# Type aliases for cleaner dependency injection
CurrentUser = Annotated[User, Depends(get_current_user)]
DBSession = Annotated[Session, Depends(get_db_session)]
IntentServiceDep = Annotated[IntentService, Depends(get_intent_service)]
SessionServiceDep = Annotated[SessionService, Depends(get_session_service)]
EmotionalChatServiceDep = Annotated[EmotionalChatService, Depends(get_emotional_chat_service)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


# ---------------------------------------------------------------------------
# Optional API signing verification (HMAC-SHA256)
# ---------------------------------------------------------------------------

async def verify_api_signature(request: Request) -> None:
    """Verify HMAC-SHA256 signature on request body + timestamp.

    The frontend should include these headers:
    - ``X-Timestamp``: Unix timestamp (seconds)
    - ``X-Signature``: Base64 HMAC-SHA256 of ``{timestamp}.{body}``

    If ``LANGWEAVE_API_SIGNING_SECRET`` is not configured, verification is skipped.
    This is an **optional** extra layer — enable it in production for sensitive routes.
    """
    settings = get_auth_settings()
    if not settings.api_signing_enabled:
        return  # signing not configured, skip

    timestamp_header = request.headers.get("X-Timestamp")
    signature_header = request.headers.get("X-Signature")

    if not timestamp_header or not signature_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Timestamp or X-Signature header",
        )

    try:
        timestamp = int(timestamp_header)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid X-Timestamp format",
        )

    body_bytes = await request.body()
    body = body_bytes.decode("utf-8") if body_bytes else ""

    if not verify_request_signature(body, timestamp, signature_header):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid request signature or timestamp expired",
        )


# Optional dependency — add to routes that need extra protection
VerifiedRequest = Annotated[None, Depends(verify_api_signature)]
