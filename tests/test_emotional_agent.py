"""Emotional agent registration tests."""

from __future__ import annotations

import asyncio

import pytest
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage

from app.domain.agents.emotional import build_emotional_agent
from app.domain.agents.registry import register_agents
from langweave.registry import AgentRegistry


def test_emotional_agent_registered() -> None:
    pytest.importorskip("langchain_deepseek")
    registry = AgentRegistry()
    register_agents(registry)
    assert "emotional" in registry.list_names()
    agent = registry.get("emotional")
    assert "情感" in agent.description or "陪伴" in agent.description


def test_emotional_agent_chat() -> None:
    fake = FakeMessagesListChatModel(
        responses=[AIMessage(content="我能理解你现在的感受，愿意多说说吗？")]
    )
    from langweave import AgentBuilder

    agent = (
        AgentBuilder()
        .with_name("emotional")
        .with_model(fake)
        .build()
    )
    reply, _ = asyncio.run(agent.achat("最近工作压力很大，很焦虑"))
    assert "理解" in reply or "说说" in reply
