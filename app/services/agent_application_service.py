"""Agent application service — entry-agent chat with intent routing.

Wraps ``app.application.services.chat.ChatService`` with the new service API.
"""
from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.orm import Session

from app.application.services.chat import ChatService
from langweave.registry import AgentRegistry
from langweave.web.serialize import json_dumps

logger = logging.getLogger(__name__)


class AgentApplicationService:
    """Application-layer service for unified agent invocation."""

    def __init__(self, db: Session, registry: AgentRegistry) -> None:
        self._chat_service = ChatService(db, registry)

    async def stream_message(
        self,
        user: Any,
        message: str,
        *,
        conversation_id: int | None = None,
    ) -> AsyncIterator[str]:
        """Stream a message through the entry agent (intent → specialist)."""
        async for event in self._chat_service.stream_message(
            user, message, conversation_id=conversation_id
        ):
            yield event

    def list_agents(self) -> list[str]:
        return self._chat_service.list_agents()  # type: ignore[attr-defined]
