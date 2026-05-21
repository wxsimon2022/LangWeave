"""FastAPI route tests."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage

from langweave import AgentBuilder
from langweave.registry import AgentRegistry
from langweave.web import create_app

from tests.conftest import unwrap_response


@pytest.fixture
def client() -> TestClient:
    registry = AgentRegistry()
    model = FakeMessagesListChatModel(
        responses=[AIMessage(content="web reply")]
    )
    agent = AgentBuilder().with_name("demo").with_model(model).build()
    registry.register(agent)

    app = create_app(registry)
    return TestClient(app)


def test_health(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    assert unwrap_response(body)["status"] == "ok"


def test_list_agents(client: TestClient) -> None:
    r = client.get("/api/v1/agents")
    assert r.status_code == 200
    assert r.json()["code"] == 200
    names = [a["name"] for a in unwrap_response(r.json())["agents"]]
    assert names == ["demo"]


def test_chat(client: TestClient) -> None:
    r = client.post(
        "/api/v1/agents/demo/chat",
        json={"message": "hello"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    assert body["message"] == ""
    data = unwrap_response(body)
    assert data["content"] == "web reply"
    assert data["agent"] == "demo"


def test_invoke(client: TestClient) -> None:
    r = client.post(
        "/api/v1/agents/demo/invoke",
        json={"message": "hi"},
    )
    assert r.status_code == 200
    assert unwrap_response(r.json())["state"]["messages"]


def test_stream(client: TestClient) -> None:
    r = client.post(
        "/api/v1/agents/demo/stream",
        json={"message": "stream"},
    )
    assert r.status_code == 200
    assert "text/event-stream" in r.headers.get("content-type", "")
    lines = [ln for ln in r.text.split("\n") if ln.startswith("data: ")]
    assert len(lines) >= 1
    last = json.loads(lines[-1].removeprefix("data: "))
    assert last["code"] == 200
    assert unwrap_response(last)["event"] == "done"


def test_unknown_agent(client: TestClient) -> None:
    r = client.post(
        "/api/v1/agents/missing/chat",
        json={"message": "x"},
    )
    assert r.status_code == 404
    body = r.json()
    assert body["code"] == 404
    assert body["data"] is None
    assert body["message"]
