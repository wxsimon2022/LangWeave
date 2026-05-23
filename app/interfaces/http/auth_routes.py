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
    decode_refresh_token,
)
from app.application.services.auth import AuthService
from app.infrastructure.cache.anomaly import (
    check_login_anomaly_sync,
    check_register_anomaly_sync,
    record_failed_login_sync,
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
        return ApiResponse.ok(service.register(body.username, body.password))
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
        return ApiResponse.ok(service.login(body.username, body.password))
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
        return ApiResponse.ok(
            AuthTokenResponse(
                access_token=create_access_token(user.id),
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
    return ApiResponse.ok({"message": "Logged out"})
