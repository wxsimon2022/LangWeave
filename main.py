"""ASGI entrypoint: uvicorn main:app --reload"""

from langweave.config import load_dotenv

load_dotenv()

from app.core.app import create_app

app = create_app()
