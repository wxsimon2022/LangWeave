"""Agent HTTP routes."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from langweave.agent import Agent
from langweave.registry import AgentRegistry
from langweave.web.deps import get_agent, get_registry
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


@router.get("", response_model=AgentListResponse)
def list_agents(
    registry: Annotated[AgentRegistry, Depends(get_registry)],
) -> AgentListResponse:
    agents = [
        AgentInfo(name=name, description=registry.get(name).description)
        for name in registry.list_names()
    ]
    return AgentListResponse(agents=agents)


@router.post("/{agent_name}/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    agent: Annotated[Agent, Depends(get_agent)],
) -> ChatResponse:
    content = await agent.achat(body.message, thread_id=body.thread_id)
    return ChatResponse(
        content=content,
        agent=agent.name,
        thread_id=body.thread_id,
    )


@router.post("/{agent_name}/invoke", response_model=InvokeResponse)
async def invoke(
    body: InvokeRequest,
    agent: Annotated[Agent, Depends(get_agent)],
) -> InvokeResponse:
    try:
        agent_input = body.to_agent_input()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    state = await agent.ainvoke(agent_input, thread_id=body.thread_id)
    return InvokeResponse(
        agent=agent.name,
        thread_id=body.thread_id,
        state=serialize_state(state),
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
        payload = json_dumps({"event": "chunk", "data": chunk})
        yield f"data: {payload}\n\n"
    yield f"data: {json_dumps({'event': 'done'})}\n\n"


@router.post("/{agent_name}/stream")
async def stream(
    body: StreamRequest,
    agent: Annotated[Agent, Depends(get_agent)],
) -> StreamingResponse:
    return StreamingResponse(
        _sse_stream(agent, body),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
