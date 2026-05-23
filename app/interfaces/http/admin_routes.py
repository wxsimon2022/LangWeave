"""Admin HTTP routes for user management."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.interfaces.http.deps import AuthServiceDep, get_current_admin_user
from app.schemas.admin import (
    AdminConversationListResponse,
    AdminConversationMessagesResponse,
    AdminCreateUserRequest,
    AdminCreateUserResponse,
    AdminUpdatePasswordRequest,
    AdminUpdatePasswordResponse,
    AdminUserDeleteResponse,
    AdminUserListResponse,
)
from app.infrastructure.persistence.models import User
from app.infrastructure.cache.heartbeat import get_online_users_async, get_online_count_async
from app.infrastructure.cache.dau import get_dau_summary_async
from langweave.web.response import ApiResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


AdminUser = Annotated[User, Depends(get_current_admin_user)]


@router.get(
    "/users",
    response_model=ApiResponse[AdminUserListResponse],
    summary="列出所有注册用户（仅管理员）",
)
async def list_users(
    _admin: AdminUser,
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
    _admin: AdminUser,
    auth_service: AuthServiceDep,
) -> ApiResponse[AdminUserDeleteResponse]:
    if user_id == _admin.id:
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


@router.get(
    "/users/{user_id}/conversations",
    response_model=ApiResponse[AdminConversationListResponse],
    summary="查看指定用户的所有对话列表（仅管理员）",
)
async def list_user_conversations(
    user_id: int,
    _admin: AdminUser,
    auth_service: AuthServiceDep,
) -> ApiResponse[AdminConversationListResponse]:
    try:
        data = auth_service.list_conversations_for_user(user_id)
        return ApiResponse.ok(data)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get(
    "/users/{user_id}/conversations/{conversation_id}",
    response_model=ApiResponse[AdminConversationMessagesResponse],
    summary="查看指定对话的所有消息（仅管理员）",
)
async def get_user_conversation_messages(
    user_id: int,
    conversation_id: int,
    _admin: AdminUser,
    auth_service: AuthServiceDep,
) -> ApiResponse[AdminConversationMessagesResponse]:
    try:
        data = auth_service.get_conversation_messages(user_id, conversation_id)
        return ApiResponse.ok(data)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.put(
    "/users/{user_id}/password",
    response_model=ApiResponse[AdminUpdatePasswordResponse],
    summary="修改指定用户的密码（仅管理员）",
)
async def update_user_password(
    user_id: int,
    body: AdminUpdatePasswordRequest,
    _admin: AdminUser,
    auth_service: AuthServiceDep,
) -> ApiResponse[AdminUpdatePasswordResponse]:
    try:
        updated_id, updated_username = auth_service.update_user_password(
            user_id, body.new_password
        )
        return ApiResponse.ok(
            AdminUpdatePasswordResponse(
                user_id=updated_id,
                username=updated_username,
            ),
            message=f"用户 {updated_username} 密码已更新",
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/users",
    response_model=ApiResponse[AdminCreateUserResponse],
    summary="创建新用户（仅管理员）",
)
async def create_user(
    body: AdminCreateUserRequest,
    _admin: AdminUser,
    auth_service: AuthServiceDep,
) -> ApiResponse[AdminCreateUserResponse]:
    try:
        user = auth_service.create_user(
            username=body.username,
            password=body.password,
            is_admin=body.is_admin,
        )
        return ApiResponse.ok(
            AdminCreateUserResponse(
                id=user.id,
                username=user.username,
                is_admin=user.is_admin,
            ),
            message=f"用户 {user.username} 已创建",
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get(
    "/users/online",
    summary="获取当前在线用户列表（仅管理员）",
)
async def get_online_users(
    _admin: AdminUser,
) -> ApiResponse[dict]:
    users = await get_online_users_async()
    count = await get_online_count_async()
    return ApiResponse.ok({
        "online_count": count,
        "online_users": users,
    })


@router.get(
    "/stats/dau",
    summary="获取 DAU 统计（仅管理员）",
)
async def get_dau_stats(
    _admin: AdminUser,
    days: int = 7,
) -> ApiResponse[dict]:
    summary = await get_dau_summary_async(days=days)
    return ApiResponse.ok(summary)
