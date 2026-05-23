"""Application composition helpers."""

from __future__ import annotations

from fastapi import FastAPI

from app.domain.agents import register_agents
from app.interfaces.http import include_business_routers
from app.infrastructure.persistence.database import get_session_factory, init_database
from app.application.security import hash_password
from app.infrastructure.persistence.models import User
from app.logging import setup_logging
from app.constants import DEFAULT_CORS_ORIGINS
from langweave.config import load_dotenv
from langweave.web import create_app
from langweave.web.swagger2 import setup_swagger2, swagger2_available

load_dotenv()
setup_logging()


def _seed_admin() -> None:
    """Create or update default admin account (admin/admin123)."""
    session_factory = get_session_factory()
    with session_factory() as session:
        admin_user = session.query(User).filter(User.username == "admin").first()
        if admin_user is None:
            session.add(
                User(
                    username="admin",
                    password_hash=hash_password("admin123"),
                )
            )
        else:
            admin_user.password_hash = hash_password("admin123")
        session.commit()


def _startup(registry) -> None:
    init_database()
    _seed_admin()
    register_agents(registry)


def create_business_app() -> FastAPI:
    """Create the project ASGI app with framework and business routes wired."""
    use_swagger2 = swagger2_available()
    app = create_app(
        on_startup=_startup,
        doc_mode="swagger2" if use_swagger2 else "openapi3",
        cors_origins=DEFAULT_CORS_ORIGINS,
    )
    include_business_routers(app)
    if use_swagger2:
        setup_swagger2(
            app,
            swagger2_url="/swagger.json",
            docs_url="/docs",
            docs_mode="both",
            swagger_ui_url="/docs/swagger",
        )
    return app
