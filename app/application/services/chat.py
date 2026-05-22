"""Chat use-case: validation, routing, and agent invocation."""

from __future__ import annotations

from langweave.agent import Agent
from langweave.registry import AgentRegistry
from app.exceptions import AgentNotFoundError, ValidationError


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
            raise ValidationError("Message cannot be empty")
        agent = self._get_agent(agent_name)
        return agent.chat(message, thread_id=thread_id)

    async def achat(
        self,
        agent_name: str,
        message: str,
        *,
        thread_id: str | None = None,
    ) -> tuple[str, str | None]:
        message = message.strip()
        if not message:
            raise ValidationError("Message cannot be empty")
        agent = self._get_agent(agent_name)
        return await agent.achat(message, thread_id=thread_id)

    def _get_agent(self, name: str) -> Agent:
        try:
            return self._registry.get(name)
        except KeyError as exc:
            raise AgentNotFoundError(name) from exc
