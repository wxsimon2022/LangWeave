"""Auth and persistent emotional chat API tests."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage

from app.infrastructure.persistence.database import init_database, reset_database_caches
from app.interfaces.http import include_business_routers
from langweave import AgentBuilder
from langweave.registry import AgentRegistry
from langweave.web import create_app
from tests.conftest import unwrap_response


def _make_client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "auth-chat.db"
    os.environ["LANGWEAVE_DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["LANGWEAVE_JWT_SECRET"] = "test-secret"
    reset_database_caches()
    init_database()

    registry = AgentRegistry()
    emotional = (
        AgentBuilder()
        .with_name("emotional")
        .with_model(
            FakeMessagesListChatModel(
                responses=[
                    AIMessage(content="我在这里陪你。"),
                    AIMessage(content="我记得你刚才提到的压力。"),
                ]
            )
        )
        .build()
    )
    registry.register(emotional, overwrite=True)

    app = create_app(registry, doc_mode="openapi3")
    include_business_routers(app)
    return TestClient(app)


def test_register_login_and_chat_history(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    register_resp = client.post(
        "/api/v1/auth/register",
        json={"username": "alice", "password": "secret123"},
    )
    assert register_resp.status_code == 201
    register_data = unwrap_response(register_resp.json())
    token = register_data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    me_resp = client.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == 200
    assert unwrap_response(me_resp.json())["username"] == "alice"

    history_resp = client.get("/api/v1/emotional-chat/history", headers=headers)
    assert history_resp.status_code == 200
    history_data = unwrap_response(history_resp.json())
    assert history_data["messages"] == []

    message_resp = client.post(
        "/api/v1/emotional-chat/messages",
        headers=headers,
        json={"message": "最近工作压力很大"},
    )
    assert message_resp.status_code == 200
    message_data = unwrap_response(message_resp.json())
    assert message_data["user_message"]["content"] == "最近工作压力很大"
    assert "陪你" in message_data["assistant_message"]["content"]

    history_resp = client.get("/api/v1/emotional-chat/history", headers=headers)
    history_data = unwrap_response(history_resp.json())
    assert len(history_data["messages"]) == 2
    assert history_data["messages"][0]["role"] == "user"
    assert history_data["messages"][1]["role"] == "assistant"

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "alice", "password": "secret123"},
    )
    assert login_resp.status_code == 200
    assert unwrap_response(login_resp.json())["user"]["username"] == "alice"


def test_emotional_chat_requires_token(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    resp = client.get("/api/v1/emotional-chat/history")
    assert resp.status_code == 401
