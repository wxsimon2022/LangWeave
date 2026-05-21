"""Conversation session history backed by LangGraph checkpointer."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage

from app.schemas.session import MessageItem, SessionHistoryResponse
from langweave.agent import Agent
from langweave.memory import aclear_thread
from langweave.registry import AgentRegistry


def _to_message_item(msg: BaseMessage) -> MessageItem:
    role = getattr(msg, "type", "unknown")
    if isinstance(msg, HumanMessage):
        role = "human"
    elif isinstance(msg, AIMessage):
        role = "ai"
    elif isinstance(msg, ToolMessage):
        role = "tool"

    content = msg.content
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        text = "".join(
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )
    else:
        text = str(content)
    return MessageItem(role=role, content=text)


class SessionService:
    """Read and clear multi-turn conversation history."""

    def __init__(self, registry: AgentRegistry) -> None:
        self._registry = registry

    def _get_agent(self, name: str) -> Agent:
        try:
            return self._registry.get(name)
        except KeyError as exc:
            msg = f"Unknown agent: {name}"
            raise ValueError(msg) from exc

    async def get_history(
        self,
        agent_name: str,
        thread_id: str,
    ) -> SessionHistoryResponse:
        agent = self._get_agent(agent_name)
        if getattr(agent.graph, "checkpointer", None) is None:
            msg = f"Agent '{agent_name}' does not enable conversation memory"
            raise ValueError(msg)

        messages = await agent.aget_history(thread_id)
        items = [_to_message_item(m) for m in messages if isinstance(m, BaseMessage)]
        return SessionHistoryResponse(
            thread_id=thread_id,
            agent=agent_name,
            message_count=len(items),
            messages=items,
        )

    async def clear(self, agent_name: str, thread_id: str) -> dict[str, Any]:
        agent = self._get_agent(agent_name)
        if getattr(agent.graph, "checkpointer", None) is None:
            msg = f"Agent '{agent_name}' does not enable conversation memory"
            raise ValueError(msg)
        await aclear_thread(agent.graph, thread_id)
        return {"thread_id": thread_id, "cleared": True}
