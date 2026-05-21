"""ASGI entrypoint: uvicorn main:app --reload"""

from langweave.config import load_dotenv

load_dotenv()

from app.agents import register_agents
from app.api.routes import router as business_router
from app.api.session_routes import router as session_router
from langweave.web import create_app
from langweave.web.swagger2 import setup_swagger2

app = create_app(on_startup=register_agents, doc_mode="swagger2")
app.include_router(business_router)
app.include_router(session_router)
setup_swagger2(
    app,
    swagger2_url="/swagger.json",
    docs_url="/docs",
    docs_mode="both",
    swagger_ui_url="/docs/swagger",
)
