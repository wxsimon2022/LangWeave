"""Chat use-case: validation, routing, and agent invocation."""

from __future__ import annotations

from langweave.agent import Agent
from langweave.registry import AgentRegistry


class ChatService:
    """Application-layer chat orchestration (non-HTTP)."""

    def __init__(self, registry: AgentRegistry) -> None:
        self._registry = registry

    def list_agents(self) -> list[str]:
        return self._registry.list_names()

    def chat(
        self,
        agent_name: str,
        message: str,
        *,
        thread_id: str | None = None,
    ) -> str:
        message = message.strip()
        if not message:
            msg = "Message cannot be empty"
            raise ValueError(msg)
        agent = self._get_agent(agent_name)
        return agent.chat(message, thread_id=thread_id)

    async def achat(
        self,
        agent_name: str,
        message: str,
        *,
        thread_id: str | None = None,
    ) -> str:
        message = message.strip()
        if not message:
            msg = "Message cannot be empty"
            raise ValueError(msg)
        agent = self._get_agent(agent_name)
        return await agent.achat(message, thread_id=thread_id)

    def _get_agent(self, name: str) -> Agent:
        try:
            return self._registry.get(name)
        except KeyError as exc:
            msg = f"Unknown agent: {name}"
            raise ValueError(msg) from exc
