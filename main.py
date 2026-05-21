"""ASGI entrypoint: uvicorn main:app --reload"""

from langweave.config import load_dotenv

load_dotenv()

from app.agents import register_agents
from langweave.web import create_app

app = create_app(on_startup=register_agents)
