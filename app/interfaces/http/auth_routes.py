"""Authentication HTTP routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.application.services.auth import AuthService
from app.interfaces.http.deps import AuthServiceDep, CurrentUser
from app.schemas.auth import AuthTokenResponse, LoginRequest, RegisterRequest, UserProfile
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


@router.get(
    "/me",
    response_model=ApiResponse[UserProfile],
    summary="当前登录用户",
)
def me(
    user: CurrentUser,
) -> ApiResponse[UserProfile]:
    return ApiResponse.ok(UserProfile.model_validate(user))
