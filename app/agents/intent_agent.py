"""Intent classification agent — structured output, no tools.

Re-exports from ``app.domain.agents.intent``.
"""
from app.domain.agents.intent import build_intent_agent, INTENT_SYSTEM_PROMPT

__all__ = ["build_intent_agent", "INTENT_SYSTEM_PROMPT"]
