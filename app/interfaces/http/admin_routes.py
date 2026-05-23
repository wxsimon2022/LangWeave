"""Admin HTTP routes for user management."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.interfaces.http.deps import AuthServiceDep, CurrentUser
from app.schemas.admin import AdminUserDeleteResponse, AdminUserListResponse
from langweave.web.response import ApiResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get(
    "/users",
    response_model=ApiResponse[AdminUserListResponse],
    summary="列出所有注册用户（仅管理员）",
)
async def list_users(
    current_user: CurrentUser,
    auth_service: AuthServiceDep,
) -> ApiResponse[AdminUserListResponse]:
    try:
        data = auth_service.list_users()
        return ApiResponse.ok(data)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete(
    "/users/{user_id}",
    response_model=ApiResponse[AdminUserDeleteResponse],
    summary="删除指定用户（仅管理员，不能删除自己）",
)
async def delete_user(
    user_id: int,
    current_user: CurrentUser,
    auth_service: AuthServiceDep,
) -> ApiResponse[AdminUserDeleteResponse]:
    if user_id == current_user.id:
        raise HTTPException(
            status_code=422,
            detail="Cannot delete yourself",
        )
    try:
        deleted_id, deleted_username = auth_service.delete_user(user_id)
        return ApiResponse.ok(
            AdminUserDeleteResponse(
                deleted_user_id=deleted_id,
                deleted_username=deleted_username,
            ),
            message=f"用户 {deleted_username} 已删除",
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
