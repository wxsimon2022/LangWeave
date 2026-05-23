"""Agent name resolution and mapping.

Maps intent types to agent names and provides helper for backward compatibility.
"""
from __future__ import annotations

from app.constants import DEFAULT_AGENT_NAME, INTENT_AGENT, ASSISTANT_AGENT, EMOTIONAL_AGENT

# Intent → agent name mapping (source of truth)
INTENT_TO_AGENT: dict[str, str] = {
    "emotional_chat": EMOTIONAL_AGENT,
    "general_chat": ASSISTANT_AGENT,
    "order_query": ASSISTANT_AGENT,
    "calculation": ASSISTANT_AGENT,
    "unknown": ASSISTANT_AGENT,
}


def get_agent_name(intent: str) -> str:
    """Resolve an intent string to the target agent name."""
    return INTENT_TO_AGENT.get(intent, DEFAULT_AGENT_NAME)
