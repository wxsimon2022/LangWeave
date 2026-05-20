"""ASGI entrypoint: uvicorn main:app --reload"""

from langweave.config import load_dotenv

load_dotenv()

from langweave import AgentBuilder
from langweave.config import AgentSettings
from langweave.tools import calculator, current_time
from langweave.web import create_app


def register_agents(registry) -> None:
    settings = AgentSettings.from_env()
    agent = (
        AgentBuilder(settings)
        .with_name("assistant")
        .with_description("General assistant with calculator and clock tools")
        .with_system_prompt(
            settings.system_prompt
            or "You are a helpful assistant. Use tools when needed."
        )
        .with_tools([calculator, current_time])
        .build()
    )
    registry.register(agent, overwrite=True)


app = create_app(on_startup=register_agents)
