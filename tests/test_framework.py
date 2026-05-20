"""Framework unit tests (no live LLM API required)."""

from __future__ import annotations

import pytest
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage

from langweave import AgentBuilder, AgentRegistry
from langweave.middleware import LoggingMiddleware
from langweave.tools import ToolRegistry, calculator, current_time
from langweave.tools.builtin import _safe_eval
import ast


def test_calculator_safe_eval() -> None:
    tree = ast.parse("2 + 3 * 4", mode="eval")
    assert _safe_eval(tree.body) == 14.0


def test_tool_registry_groups() -> None:
    reg = ToolRegistry()
    reg.register("math", calculator)
    reg.register("time", current_time)
    assert reg.groups() == ["math", "time"]
    assert len(reg.tools_for(["math"])) == 1


def test_agent_builder_compiles() -> None:
    model = FakeMessagesListChatModel(
        responses=[AIMessage(content="hello from fake model")]
    )
    agent = (
        AgentBuilder()
        .with_name("test")
        .with_model(model)
        .with_system_prompt("You are a test assistant.")
        .with_middleware(LoggingMiddleware())
        .build()
    )
    result = agent.invoke("hi")
    assert "messages" in result
    assert agent.chat("hi") == "hello from fake model"


def test_agent_registry() -> None:
    model = FakeMessagesListChatModel(responses=[AIMessage(content="ok")])
    registry = AgentRegistry()
    agent = AgentBuilder().with_name("greeter").with_model(model).build()
    registry.register(agent)
    assert registry.get("greeter").chat("x") == "ok"
    assert registry.list_names() == ["greeter"]


def test_registry_duplicate_raises() -> None:
    model = FakeMessagesListChatModel(responses=[AIMessage(content="ok")])
    registry = AgentRegistry()
    agent = AgentBuilder().with_name("a").with_model(model).build()
    registry.register(agent)
    with pytest.raises(KeyError):
        registry.register(agent)


def test_stream_yields_chunks() -> None:
    model = FakeMessagesListChatModel(responses=[AIMessage(content="streamed")])
    agent = AgentBuilder().with_model(model).build()
    chunks = list(agent.stream("ping", stream_mode="updates"))
    assert len(chunks) >= 1
