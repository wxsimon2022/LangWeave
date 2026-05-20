"""Run the agents API with uvicorn."""

from __future__ import annotations

import uvicorn

from langweave import AgentBuilder
from langweave.tools import calculator, current_time
from langweave.web import create_app


def register_agents(registry) -> None:
    agent = (
        AgentBuilder()
        .with_name("assistant")
        .with_model("openai:gpt-4o-mini")
        .with_system_prompt("You are a helpful assistant. Use tools when needed.")
        .with_tools([calculator, current_time])
        .build()
    )
    registry.register(agent, overwrite=True)


app = create_app(on_startup=register_agents)


if __name__ == "__main__":
    uvicorn.run(
        "examples.fastapi_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
