"""In-memory registry for named agents."""

from __future__ import annotations

from langweave.agent import Agent
from langweave.builder import AgentBuilder


class AgentRegistry:
    """Register and retrieve agents by name."""

    def __init__(self) -> None:
        self._agents: dict[str, Agent] = {}

    def register(self, agent: Agent, *, overwrite: bool = False) -> None:
        if agent.name in self._agents and not overwrite:
            msg = f"Agent '{agent.name}' already registered"
            raise KeyError(msg)
        self._agents[agent.name] = agent

    def get(self, name: str) -> Agent:
        try:
            return self._agents[name]
        except KeyError as exc:
            msg = f"Unknown agent: {name}"
            raise KeyError(msg) from exc

    def list_names(self) -> list[str]:
        return sorted(self._agents)

    def unregister(self, name: str) -> None:
        del self._agents[name]

    def build_and_register(
        self,
        builder: AgentBuilder,
        *,
        name: str,
        overwrite: bool = False,
    ) -> Agent:
        agent = builder.with_name(name).build()
        self.register(agent, overwrite=overwrite)
        return agent
