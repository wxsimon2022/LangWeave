"""ASGI entrypoint: uvicorn main:app --reload"""

from langweave.config import load_dotenv

load_dotenv()

from app.bootstrap import create_business_app

app = create_business_app()
