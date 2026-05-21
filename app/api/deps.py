"""FastAPI dependencies for business routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.services.intent_service import IntentService
from app.services.session_service import SessionService
from langweave.registry import AgentRegistry
from langweave.web.deps import get_registry


def get_intent_service(
    registry: Annotated[AgentRegistry, Depends(get_registry)],
) -> IntentService:
    return IntentService(registry)


def get_session_service(
    registry: Annotated[AgentRegistry, Depends(get_registry)],
) -> SessionService:
    return SessionService(registry)
