"""Agent base class wrapping a compiled LangGraph agent.

Re-exports ``Agent`` from the ``langweave`` framework for convenience.
All business agents should be built via ``AgentBuilder`` (see ``app/agents/``).
"""

from langweave import Agent

__all__ = ["Agent"]
