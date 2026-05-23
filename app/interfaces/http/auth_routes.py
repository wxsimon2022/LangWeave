"""Authentication HTTP routes."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

logger = logging.getLogger(__name__)

from app.application.security import (
    create_access_token,
    decode_access_token_with_jti,
    decode_refresh_token,
)
from app.application.services.auth import AuthService
from app.infrastructure.cache.anomaly import (
    check_login_anomaly_sync,
    check_register_anomaly_sync,
    record_failed_login_sync,
)
from app.infrastructure.cache.session import (
    clear_active_session_async,
    set_active_session_async,
)
from app.infrastructure.cache.token_blacklist import blacklist_token_async
from app.interfaces.http.deps import AuthServiceDep, CurrentUser
from app.schemas.auth import (
    AuthTokenResponse,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    UserProfile,
)

bearer_scheme = HTTPBearer(auto_error=False)
from app.constants import API_V1_AUTH
from langweave.web.response import ApiResponse

router = APIRouter(prefix=API_V1_AUTH, tags=["auth"])


@router.post(
    "/register",
    response_model=ApiResponse[AuthTokenResponse],
    status_code=status.HTTP_201_CREATED,
    summary="注册用户",
)
def register(
    body: RegisterRequest,
    service: AuthServiceDep,
    request: Request,
) -> ApiResponse[AuthTokenResponse]:
    # 异常检测：同一 IP 注册过多账号
    client_ip = request.client.host if request.client else "unknown"
    is_anomaly, reason = check_register_anomaly_sync(client_ip, body.username)
    if is_anomaly:
        logger.warning("Register anomaly: %s", reason)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Registration limit reached from this IP. Please try later.",
        )
    try:
        response = service.register(body.username, body.password)
        # Single-device: set active session for new user
        _replace_active_session(response, body.username)
        return ApiResponse.ok(response)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/login",
    response_model=ApiResponse[AuthTokenResponse],
    summary="用户登录",
)
def login(
    body: LoginRequest,
    service: AuthServiceDep,
    request: Request,
) -> ApiResponse[AuthTokenResponse]:
    # 异常检测：暴力登录尝试
    client_ip = request.client.host if request.client else "unknown"
    is_anomaly, reason = check_login_anomaly_sync(client_ip, body.username)
    if is_anomaly:
        logger.warning("Login anomaly: %s", reason)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try later.",
        )
    try:
        response = service.login(body.username, body.password)
        # Single-device: invalidate any existing active session and set new one
        _replace_active_session(response, body.username)
        return ApiResponse.ok(response)
    except ValueError as exc:
        # 记录失败尝试
        record_failed_login_sync(client_ip, body.username)
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@router.post(
    "/refresh",
    response_model=ApiResponse[AuthTokenResponse],
    summary="刷新 access token",
)
def refresh(
    body: RefreshTokenRequest,
    service: AuthServiceDep,
) -> ApiResponse[AuthTokenResponse]:
    try:
        user_id = decode_refresh_token(body.refresh_token)
        user = service.get_user(user_id)
        new_access_token = create_access_token(user.id)
        # Extract jti from the new token and set as active session
        _, new_jti = decode_access_token_with_jti(new_access_token)
        _run_async(set_active_session_async(user.id, new_jti))
        return ApiResponse.ok(
            AuthTokenResponse(
                access_token=new_access_token,
                token_type="bearer",
                user=UserProfile.model_validate(user),
            )
        )
    except (JWTError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        ) from exc


@router.get(
    "/me",
    response_model=ApiResponse[UserProfile],
    summary="当前登录用户",
)
def me(
    user: CurrentUser,
) -> ApiResponse[UserProfile]:
    return ApiResponse.ok(UserProfile.model_validate(user))


@router.post(
    "/logout",
    summary="注销登录（将当前 token 加入黑名单）",
)
async def logout(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> ApiResponse[dict]:
    if credentials is not None:
        await blacklist_token_async(credentials.credentials)
        # Clear active session so kicked detection stops immediately
        try:
            user_id, _ = decode_access_token_with_jti(credentials.credentials)
            await clear_active_session_async(user_id)
            logger.info("Cleared active session for user %s", user_id)
        except (JWTError, ValueError):
            pass  # token already invalid, nothing to clear
    return ApiResponse.ok({"message": "Logged out"})


# ---------------------------------------------------------------------------
# Single-device login helpers
# ---------------------------------------------------------------------------


def _replace_active_session(response: AuthTokenResponse, _username: str) -> None:
    """Invalidate previous session and store the new access token's jti.

    Called synchronously from login/register routes.
    """
    _, jti = decode_access_token_with_jti(response.access_token)
    _run_async(set_active_session_async(response.user.id, jti))


def _run_async(coro):
    """Run a single async coroutine from a sync context."""
    import asyncio

    try:
        asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(coro)
        finally:
            loop.close()
