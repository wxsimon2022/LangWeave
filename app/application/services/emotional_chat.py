"""Persistent emotional chat backed by DB history and the emotional agent."""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.infrastructure.persistence.models import ChatMessage, Conversation, User
from app.schemas.emotional_chat import (
    EmotionalChatResponse,
    EmotionalConversationResponse,
    EmotionalMessageItem,
)
from app.utils import chunk_to_text, last_ai_content
from langweave.agent import Agent
from langweave.web.serialize import json_dumps
from langweave.memory import aclear_thread
from langweave.registry import AgentRegistry
from app.exceptions import AgentNotFoundError, ValidationError

logger = logging.getLogger(__name__)
DEFAULT_PAGE_LIMIT = 50


def _message_to_schema(message: ChatMessage) -> EmotionalMessageItem:
    return EmotionalMessageItem(
        id=message.id,
        role=message.role,
        content=message.content,
        created_at=message.created_at,
    )


def _safe_yield(event: str, payload: Any) -> str | None:
    """Build an SSE string. Returns None if the generator is shutting down."""
    try:
        return EmotionalChatService._sse_event(event, payload)
    except Exception:
        return None


class EmotionalChatService:
    """Persist and replay emotional chat history for authenticated users."""

    AGENT_NAME = "emotional"

    def __init__(self, db: Session, registry: AgentRegistry) -> None:
        self._db = db
        self._registry = registry

    async def get_history(
        self,
        user: User,
        *,
        offset: int = 0,
        limit: int = DEFAULT_PAGE_LIMIT,
    ) -> EmotionalConversationResponse:
        conversation = self._get_or_create_conversation(user.id)
        total_count = len(conversation.messages)
        page = conversation.messages[offset : offset + limit]
        has_more = offset + limit < total_count
        return EmotionalConversationResponse(
            conversation_id=conversation.id,
            thread_id=conversation.thread_id,
            agent=conversation.agent_name,
            messages=[_message_to_schema(m) for m in page],
            total_count=total_count,
            offset=offset,
            limit=limit,
            has_more=has_more,
        )

    async def send_message(self, user: User, message: str) -> EmotionalChatResponse:
        content = message.strip()
        if not content:
            raise ValidationError("Message cannot be empty")

        conversation = self._get_or_create_conversation(user.id)
        agent = self._get_emotional_agent()
        history = [self._to_langchain_message(item) for item in conversation.messages]
        if getattr(agent.graph, "checkpointer", None) is not None:
            await aclear_thread(agent.graph, conversation.thread_id)
        state = await agent.ainvoke(
            {"messages": [*history, HumanMessage(content=content)]},
            thread_id=conversation.thread_id,
        )
        reply = last_ai_content(state.get("messages", []))
        if not reply:
            raise ValidationError("Agent returned an empty response")

        user_message = ChatMessage(
            conversation_id=conversation.id,
            role="user",
            content=content,
        )
        assistant_message = ChatMessage(
            conversation_id=conversation.id,
            role="assistant",
            content=reply,
        )
        self._db.add_all([user_message, assistant_message])
        conversation.updated_at = datetime.now(timezone.utc)
        self._db.commit()
        self._db.refresh(user_message)
        self._db.refresh(assistant_message)
        self._db.refresh(conversation)

        return EmotionalChatResponse(
            conversation_id=conversation.id,
            thread_id=conversation.thread_id,
            agent=conversation.agent_name,
            user_message=_message_to_schema(user_message),
            assistant_message=_message_to_schema(assistant_message),
        )

    async def stream_message(
        self,
        user: User,
        message: str,
    ) -> AsyncIterator[str]:
        content = message.strip()
        if not content:
            raise ValidationError("Message cannot be empty")

        conversation = self._get_or_create_conversation(user.id)
        agent = self._get_emotional_agent()

        history = [self._to_langchain_message(item) for item in conversation.messages]
        if getattr(agent.graph, "checkpointer", None) is not None:
            await aclear_thread(agent.graph, conversation.thread_id)

        final_reply = ""

        try:
            async for chunk in agent.astream(
                {"messages": [*history, HumanMessage(content=content)]},
                thread_id=conversation.thread_id,
                stream_mode="messages",
            ):
                text = chunk_to_text(chunk)
                if not text:
                    continue
                final_reply += text
                yield self._sse_event("chunk", {"content": text})
        except GeneratorExit:
            # Client disconnected — stop without persisting
            return
        except BaseException:
            # Any other error: log, skip DB persistence, stop
            logger.exception("Emotional chat stream error")
            return

        if not final_reply:
            final_reply = "我在这里陪着你。"

        user_message = ChatMessage(
            conversation_id=conversation.id,
            role="user",
            content=content,
        )
        assistant_message = ChatMessage(
            conversation_id=conversation.id,
            role="assistant",
            content=final_reply,
        )
        self._db.add_all([user_message, assistant_message])
        conversation.updated_at = datetime.now(timezone.utc)
        self._db.commit()

        yield self._sse_event(
            "done",
            EmotionalChatResponse(
                conversation_id=conversation.id,
                thread_id=conversation.thread_id,
                agent=conversation.agent_name,
                user_message=_message_to_schema(user_message),
                assistant_message=_message_to_schema(assistant_message),
            ).model_dump(mode="json"),
        )

    async def reset_history(self, user: User) -> EmotionalConversationResponse:
        conversation = self._get_or_create_conversation(user.id)
        for message in list(conversation.messages):
            self._db.delete(message)
        conversation.thread_id = str(uuid.uuid4())
        conversation.updated_at = datetime.now(timezone.utc)
        self._db.commit()
        self._db.refresh(conversation)
        return EmotionalConversationResponse(
            conversation_id=conversation.id,
            thread_id=conversation.thread_id,
            agent=conversation.agent_name,
            messages=[],
            total_count=0,
            has_more=False,
        )

    def _get_or_create_conversation(self, user_id: int) -> Conversation:
        conversation = self._db.scalar(
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(
                Conversation.user_id == user_id,
                Conversation.agent_name == self.AGENT_NAME,
            )
        )
        if conversation is not None:
            return conversation

        conversation = Conversation(user_id=user_id, agent_name=self.AGENT_NAME)
        self._db.add(conversation)
        self._db.commit()
        self._db.refresh(conversation)
        conversation = self._db.scalar(
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(Conversation.id == conversation.id)
        )
        if conversation is None:
            msg = "Failed to initialize conversation"
            raise ValueError(msg)
        return conversation

    def _get_emotional_agent(self) -> Agent:
        try:
            return self._registry.get(self.AGENT_NAME)
        except KeyError as exc:
            raise AgentNotFoundError(self.AGENT_NAME) from exc

    @staticmethod
    def _to_langchain_message(message: ChatMessage) -> BaseMessage:
        if message.role == "assistant":
            return AIMessage(content=message.content)
        if message.role == "system":
            return SystemMessage(content=message.content)
        return HumanMessage(content=message.content)

    @staticmethod
    def _sse_event(event: str, payload: dict[str, Any]) -> str:
        data = json_dumps({"event": event, "payload": payload})
        return f"data: {data}\n\n"
