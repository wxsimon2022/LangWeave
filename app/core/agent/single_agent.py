"""Single-agent invocation helpers."""
from __future__ import annotations

from typing import Any

from langweave import Agent


async def achat(agent: Agent, message: str, thread_id: str | None = None) -> tuple[str, str | None]:
    """Send a single message to an agent and get the reply."""
    return await agent.achat(message, thread_id=thread_id)
