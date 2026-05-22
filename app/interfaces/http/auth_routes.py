"""Authentication HTTP routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.application.services.auth import AuthService
from app.infrastructure.persistence.models import User
from app.interfaces.http.deps import get_auth_service, get_current_user
from app.schemas.auth import AuthTokenResponse, LoginRequest, RegisterRequest, UserProfile
from langweave.web.response import ApiResponse

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=ApiResponse[AuthTokenResponse],
    status_code=status.HTTP_201_CREATED,
    summary="注册用户",
)
def register(
    body: RegisterRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
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
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> ApiResponse[AuthTokenResponse]:
    try:
        return ApiResponse.ok(service.login(body.username, body.password))
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@router.get(
    "/me",
    response_model=ApiResponse[UserProfile],
    summary="当前登录用户",
)
def me(
    user: Annotated[User, Depends(get_current_user)],
) -> ApiResponse[UserProfile]:
    return ApiResponse.ok(UserProfile.model_validate(user))
