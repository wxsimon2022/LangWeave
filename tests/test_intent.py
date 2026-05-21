"""Intent service and API tests."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.schemas.intent import UserIntent
from app.services.intent_service import IntentService
from langweave.registry import AgentRegistry
from langweave.web import create_app


@pytest.fixture
def intent_service() -> IntentService:
    registry = AgentRegistry()
    intent_agent = MagicMock()
    intent_agent.ainvoke = AsyncMock(
        return_value={
            "structured_response": UserIntent(
                intent="order_query",
                confidence=0.92,
                slots={"order_id": "10001"},
                target_agent="assistant",
                reasoning="用户询问订单",
            )
        }
    )
    worker = MagicMock()
    worker.achat = AsyncMock(return_value="订单已发货")
    registry.register(intent_agent, overwrite=True)
    intent_agent.name = "intent"
    registry._agents["intent"] = intent_agent
    registry._agents["assistant"] = worker
    worker.name = "assistant"
    return IntentService(registry)


def test_recognize_structured(intent_service: IntentService) -> None:
    result = asyncio.run(intent_service.recognize("查一下订单10001"))
    assert result.intent == "order_query"
    assert result.slots["order_id"] == "10001"


def test_recognize_and_chat(intent_service: IntentService) -> None:
    result = asyncio.run(intent_service.recognize_and_chat("查一下订单10001"))
    assert result.reply == "订单已发货"
    assert result.agent == "assistant"


def test_intent_api_recognize() -> None:
    registry = AgentRegistry()
    intent_agent = MagicMock()
    intent_agent.name = "intent"
    intent_agent.ainvoke = AsyncMock(
        return_value={
            "structured_response": UserIntent(
                intent="calculation",
                confidence=0.88,
                slots={"expression": "1+2"},
                target_agent="assistant",
            )
        }
    )
    registry._agents["intent"] = intent_agent

    from app.api.routes import router as business_router

    app = create_app(registry)
    app.include_router(business_router)

    client = TestClient(app)
    r = client.post(
        "/api/v1/intent/recognize",
        json={"message": "1+2等于几"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    assert body["data"]["intent"]["intent"] == "calculation"
