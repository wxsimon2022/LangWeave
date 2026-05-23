"""Fallback agent — used when model dependencies are unavailable.

Re-exports from ``app.domain.agents.fallback``.
"""
from app.domain.agents.fallback import UnavailableAgent, build_unavailable_agent

__all__ = ["UnavailableAgent", "build_unavailable_agent"]
