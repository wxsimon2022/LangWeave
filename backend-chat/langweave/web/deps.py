"""FastAPI dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from langweave.agent import Agent
from langweave.registry import AgentRegistry


def get_registry(request: Request) -> AgentRegistry:
    registry: AgentRegistry | None = getattr(request.app.state, "registry", None)
    if registry is None:
        msg = "AgentRegistry not configured on app.state"
        raise RuntimeError(msg)
    return registry


def get_agent(
    agent_name: str,
    registry: Annotated[AgentRegistry, Depends(get_registry)],
) -> Agent:
    try:
        return registry.get(agent_name)
    except KeyError as exc:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail=str(exc)) from exc
