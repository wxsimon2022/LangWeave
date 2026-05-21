"""Business layer tests."""

from __future__ import annotations

import pytest
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage

from app.services import ChatService
from app.tools.order import query_order_status
from langweave.registry import AgentRegistry


def test_query_order_status_tool() -> None:
    assert "shipped" in query_order_status.invoke({"order_id": "10001"})


def test_chat_service_invokes_agent() -> None:
    from langweave import AgentBuilder

    fake = FakeMessagesListChatModel(responses=[AIMessage(content="ok")])
    agent = (
        AgentBuilder()
        .with_name("assistant")
        .with_model(fake)
        .build()
    )
    registry = AgentRegistry()
    registry.register(agent)
    svc = ChatService(registry)
    assert svc.chat("assistant", "hi") == "ok"


def test_chat_service_empty_message() -> None:
    from langweave import AgentBuilder

    registry = AgentRegistry()
    registry.register(
        AgentBuilder().with_name("assistant").with_model(
            FakeMessagesListChatModel(responses=[AIMessage(content="x")])
        ).build(),
    )
    svc = ChatService(registry)
    with pytest.raises(ValueError, match="empty"):
        svc.chat("assistant", "   ")
