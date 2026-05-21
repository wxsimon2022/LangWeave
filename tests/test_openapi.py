"""Swagger 2 / OpenAPI documentation tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api import include_business_routers
from langweave.web import create_app
from langweave.web.swagger2 import setup_swagger2

pytest.importorskip("fastapi_swagger2")


def _client_swagger2() -> TestClient:
    app = create_app(doc_mode="swagger2")
    include_business_routers(app)
    setup_swagger2(app)
    return TestClient(app)


def _client_openapi3() -> TestClient:
    app = create_app(doc_mode="openapi3")
    include_business_routers(app)
    return TestClient(app)


def test_swagger2_json() -> None:
    client = _client_swagger2()
    r = client.get("/swagger.json")
    assert r.status_code == 200
    schema = r.json()
    assert schema["swagger"] == "2.0"
    assert "/api/v1/agents/{agent_name}/chat" in schema["paths"]
    assert "/api/v1/intent/recognize" in schema["paths"]


def test_tree_docs_page() -> None:
    client = _client_swagger2()
    r = client.get("/docs")
    assert r.status_code == 200
    assert "在线调试" in r.text
    assert "发送请求" in r.text


def test_swagger2_classic_ui() -> None:
    client = _client_swagger2()
    r = client.get("/docs/swagger")
    assert r.status_code == 200


def test_openapi3_still_available_when_enabled() -> None:
    client = _client_openapi3()
    r = client.get("/openapi.json")
    assert r.status_code == 200
    assert r.json()["openapi"].startswith("3.")
