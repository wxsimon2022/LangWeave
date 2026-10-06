"""Agent HTTP routes."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from langweave.agent import Agent
from langweave.registry import AgentRegistry
from langweave.web.deps import get_agent, get_registry
from langweave.web.response import ApiResponse
from langweave.web.schemas import (
    AgentInfo,
    AgentListResponse,
    ChatRequest,
    ChatResponse,
    InvokeRequest,
    InvokeResponse,
    StreamRequest,
)
from langweave.web.serialize import json_dumps, serialize_state

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


@router.get(
    "",
    response_model=ApiResponse[AgentListResponse],
    summary="列出已注册 Agent",
)
def list_agents(
    registry: Annotated[AgentRegistry, Depends(get_registry)],
) -> ApiResponse[AgentListResponse]:
    """返回当前注册表中所有 Agent 的名称与描述。"""
    agents = [
        AgentInfo(name=name, description=registry.get(name).description)
        for name in registry.list_names()
    ]
    return ApiResponse.ok(AgentListResponse(agents=agents))


@router.post(
    "/{agent_name}/chat",
    response_model=ApiResponse[ChatResponse],
    summary="Agent 对话",
)
async def chat(
    body: ChatRequest,
    agent: Annotated[Agent, Depends(get_agent)],
) -> ApiResponse[ChatResponse]:
    """向指定 Agent 发送用户消息，返回模型回复文本。"""
    content, thread_id = await agent.achat(body.message, thread_id=body.thread_id)
    return ApiResponse.ok(
        ChatResponse(
            content=content,
            agent=agent.name,
            thread_id=thread_id or body.thread_id,
        )
    )


@router.post(
    "/{agent_name}/invoke",
    response_model=ApiResponse[InvokeResponse],
    summary="完整调用 Agent",
)
async def invoke(
    body: InvokeRequest,
    agent: Annotated[Agent, Depends(get_agent)],
) -> ApiResponse[InvokeResponse]:
    """调用 LangGraph，返回完整 state（含 messages、structured_response 等）。"""
    try:
        agent_input = body.to_agent_input()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    state = await agent.ainvoke(agent_input, thread_id=body.thread_id)
    return ApiResponse.ok(
        InvokeResponse(
            agent=agent.name,
            thread_id=body.thread_id,
            state=serialize_state(state),
        )
    )


async def _sse_stream(
    agent: Agent,
    body: StreamRequest,
) -> AsyncIterator[str]:
    async for chunk in agent.astream(
        body.message,
        thread_id=body.thread_id,
        stream_mode=body.stream_mode,
    ):
        envelope = ApiResponse.ok({"event": "chunk", "payload": chunk})
        yield f"data: {json_dumps(envelope.model_dump())}\n\n"
    done = ApiResponse.ok({"event": "done"})
    yield f"data: {json_dumps(done.model_dump())}\n\n"


@router.post(
    "/{agent_name}/stream",
    summary="SSE 流式输出",
    response_class=StreamingResponse,
    responses={
        200: {
            "description": "SSE，每条 data 为 {code, message, data}  envelope",
            "content": {"text/event-stream": {}},
        },
    },
)
async def stream(
    body: StreamRequest,
    agent: Annotated[Agent, Depends(get_agent)],
) -> StreamingResponse:
    """以 SSE 推送 Agent 执行过程；每条消息均为统一响应格式。"""
    return StreamingResponse(
        _sse_stream(agent, body),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
