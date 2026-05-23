"""Authentication HTTP routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from jose import JWTError

from app.application.security import (
    create_access_token,
    decode_refresh_token,
)
from app.application.services.auth import AuthService
from app.interfaces.http.deps import AuthServiceDep, CurrentUser
from app.schemas.auth import (
    AuthTokenResponse,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    UserProfile,
)
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
) -> ApiResponse[AuthTokenResponse]:
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
) -> ApiResponse[AuthTokenResponse]:
    try:
        return ApiResponse.ok(service.login(body.username, body.password))
    except ValueError as exc:
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
