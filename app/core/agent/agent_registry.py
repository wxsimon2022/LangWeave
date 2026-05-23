"""Agent registration and lookup.

Re-exports ``AgentRegistry`` from the ``langweave`` framework.
"""
from langweave.registry import AgentRegistry as _AgentRegistry

AgentRegistry = _AgentRegistry

__all__ = ["AgentRegistry"]
