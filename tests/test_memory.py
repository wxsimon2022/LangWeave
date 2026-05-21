"""Multi-turn conversation memory tests."""

from __future__ import annotations

import asyncio

import pytest
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, HumanMessage

from langweave import AgentBuilder
from langweave.memory import MemorySaver, get_thread_messages


def test_multi_turn_memory() -> None:
    fake = FakeMessagesListChatModel(
        responses=[
            AIMessage(content="第一轮回复"),
            AIMessage(content="我记得你"),
        ]
    )
    agent = (
        AgentBuilder()
        .with_model(fake)
        .with_checkpointer(MemorySaver())
        .build()
    )
    tid = "session-test-1"
    asyncio.run(agent.achat("你好", thread_id=tid))
    reply, returned_tid = asyncio.run(agent.achat("你还记得吗", thread_id=tid))
    assert returned_tid == tid
    assert reply == "我记得你"

    history = get_thread_messages(agent.graph, tid)
    assert len(history) >= 4
    human_msgs = [m for m in history if isinstance(m, HumanMessage)]
    assert len(human_msgs) >= 2


def test_auto_thread_id_when_checkpointer() -> None:
    fake = FakeMessagesListChatModel(responses=[AIMessage(content="ok")])
    agent = (
        AgentBuilder()
        .with_model(fake)
        .with_checkpointer(MemorySaver())
        .build()
    )
    _, tid = asyncio.run(agent.achat("hi"))
    assert tid is not None
    assert len(tid) > 0


def test_emotional_agent_has_checkpointer() -> None:
    from app.agents.emotional import build_emotional_agent

    agent = build_emotional_agent()
    assert getattr(agent.graph, "checkpointer", None) is not None
