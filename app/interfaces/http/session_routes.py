"""Session / memory HTTP routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.application.services.session import SessionService
from app.interfaces.http.deps import SessionServiceDep
from app.schemas.session import SessionHistoryResponse
from app.constants import API_V1_SESSIONS
from langweave.web.response import ApiResponse

router = APIRouter(prefix=API_V1_SESSIONS, tags=["sessions"])


@router.get(
    "/{agent_name}/{thread_id}",
    response_model=ApiResponse[SessionHistoryResponse],
    summary="获取会话历史",
)
async def get_session_history(
    agent_name: str,
    thread_id: str,
    service: SessionServiceDep,
) -> ApiResponse[SessionHistoryResponse]:
    """返回指定 thread_id 下已记住的多轮消息。"""
    try:
        history = await service.get_history(agent_name, thread_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ApiResponse.ok(history)


@router.delete(
    "/{agent_name}/{thread_id}",
    response_model=ApiResponse[dict],
    summary="清空会话记忆",
)
async def clear_session(
    agent_name: str,
    thread_id: str,
    service: SessionServiceDep,
) -> ApiResponse[dict]:
    """清空该会话的上下文，开始新对话。"""
    try:
        result = await service.clear(agent_name, thread_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ApiResponse.ok(result, message="会话已清空")
