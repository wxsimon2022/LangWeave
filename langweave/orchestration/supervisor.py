"""Supervisor pattern: one coordinator agent delegates to specialists."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field

from langweave.agent import Agent
from langweave.builder import AgentBuilder


def create_handoff_tool(
    agent: Agent,
    *,
    name: str | None = None,
    description: str | None = None,
) -> BaseTool:
    """Wrap a specialist agent as a tool the supervisor can call."""

    tool_name = name or f"ask_{agent.name}"
    tool_description = description or (
        f"Delegate a sub-task to the '{agent.name}' specialist. "
        f"{agent.description}".strip()
    )

    class HandoffInput(BaseModel):
        task: str = Field(description="Clear task description for the specialist")

    def _run(task: str) -> str:
        return agent.chat(task)

    return StructuredTool.from_function(
        func=_run,
        name=tool_name,
        description=tool_description,
        args_schema=HandoffInput,
    )


class SupervisorBuilder:
    """Build a supervisor agent with handoff tools to workers."""

    def __init__(
        self,
        workers: dict[str, Agent],
        *,
        model: str | None = None,
        system_prompt: str | None = None,
    ) -> None:
        self._workers = workers
        self._model = model
        self._system_prompt = system_prompt or _default_supervisor_prompt(workers)

    def build(self) -> Agent:
        handoffs = [
            create_handoff_tool(agent, name=f"ask_{name}")
            for name, agent in self._workers.items()
        ]
        builder = (
            AgentBuilder()
            .with_name("supervisor")
            .with_description("Coordinates specialist agents")
            .with_system_prompt(self._system_prompt)
            .with_tools(handoffs)
        )
        if self._model:
            builder.with_model(self._model)
        return builder.build()


def _default_supervisor_prompt(workers: dict[str, Agent]) -> str:
    names = ", ".join(workers)
    return (
        "You are a supervisor that routes work to specialist agents.\n"
        f"Available specialists: {names}.\n"
        "Break down the user request, call the right specialist tool(s), "
        "and synthesize a final answer."
    )
