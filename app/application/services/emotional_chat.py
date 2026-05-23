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
    ConversationListResponse,
    ConversationSummary,
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


class EmotionalChatService:
    """Persist and replay emotional chat history for authenticated users."""

    AGENT_NAME = "emotional"

    def __init__(self, db: Session, registry: AgentRegistry) -> None:
        self._db = db
        self._registry = registry

    # ------------------------------------------------------------------
    # Conversation listing
    # ------------------------------------------------------------------

    async def list_conversations(self, user: User) -> ConversationListResponse:
        """Return all conversations for the current user, newest first."""
        stmt = (
            select(Conversation)
            .where(
                Conversation.user_id == user.id,
                Conversation.agent_name == self.AGENT_NAME,
            )
            .options(selectinload(Conversation.messages))
            .order_by(Conversation.updated_at.desc())
        )
        convs = list(self._db.scalars(stmt).unique().all())
        summaries = [
            ConversationSummary(
                id=c.id,
                title=c.title,
                agent=c.agent_name,
                message_count=len(c.messages),
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in convs
        ]
        return ConversationListResponse(conversations=summaries)

    # ------------------------------------------------------------------
    # Create / get conversation
    # ------------------------------------------------------------------

    def _get_conversation(self, user_id: int, conv_id: int) -> Conversation | None:
        return self._db.scalar(
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(
                Conversation.id == conv_id,
                Conversation.user_id == user_id,
                Conversation.agent_name == self.AGENT_NAME,
            )
        )

    def _create_conversation(self, user_id: int) -> Conversation:
        conv = Conversation(user_id=user_id, agent_name=self.AGENT_NAME)
        self._db.add(conv)
        self._db.commit()
        self._db.refresh(conv)
        # reload with messages eager-loaded
        reloaded = self._db.scalar(
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(Conversation.id == conv.id)
        )
        if reloaded is None:
            msg = "Failed to initialize conversation"
            raise ValueError(msg)
        return reloaded

    def _resolve_conversation(self, user_id: int, conv_id: int | None) -> Conversation:
        """Return the requested conversation, or create a new one."""
        if conv_id is not None:
            conv = self._get_conversation(user_id, conv_id)
            if conv is not None:
                return conv
            raise ValidationError(f"Conversation {conv_id} not found")
        return self._create_conversation(user_id)

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    async def get_history(
        self,
        user: User,
        *,
        conversation_id: int,
        offset: int = 0,
        limit: int = DEFAULT_PAGE_LIMIT,
    ) -> EmotionalConversationResponse:
        conv = self._get_conversation(user.id, conversation_id)
        if conv is None:
            raise ValidationError(f"Conversation {conversation_id} not found")
        total_count = len(conv.messages)
        page = conv.messages[offset : offset + limit]
        has_more = offset + limit < total_count
        return EmotionalConversationResponse(
            conversation_id=conv.id,
            thread_id=conv.thread_id,
            agent=conv.agent_name,
            messages=[_message_to_schema(m) for m in page],
            total_count=total_count,
            offset=offset,
            limit=limit,
            has_more=has_more,
        )

    # ------------------------------------------------------------------
    # Send message (sync)
    # ------------------------------------------------------------------

    async def send_message(
        self,
        user: User,
        message: str,
        *,
        conversation_id: int | None = None,
    ) -> EmotionalChatResponse:
        content = message.strip()
        if not content:
            raise ValidationError("Message cannot be empty")

        conversation = self._resolve_conversation(user.id, conversation_id)
        agent = self._get_emotional_agent()
        history = [
            self._to_langchain_message(item) for item in conversation.messages
        ]
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
        self._auto_title(conversation, content)
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

    # ------------------------------------------------------------------
    # Stream message
    # ------------------------------------------------------------------

    async def stream_message(
        self,
        user: User,
        message: str,
        *,
        conversation_id: int | None = None,
    ) -> AsyncIterator[str]:
        content = message.strip()
        if not content:
            raise ValidationError("Message cannot be empty")

        conversation = self._resolve_conversation(user.id, conversation_id)
        agent = self._get_emotional_agent()

        history = [
            self._to_langchain_message(item) for item in conversation.messages
        ]
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
            return
        except Exception:
            logger.exception("Emotional chat stream error")
            yield self._sse_event(
                "error", {"message": "Stream error, please try again"}
            )
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
        self._auto_title(conversation, content)
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

    # ------------------------------------------------------------------
    # Reset (delete all messages in a conversation)
    # ------------------------------------------------------------------

    async def reset_history(
        self, user: User, *, conversation_id: int
    ) -> EmotionalConversationResponse:
        conv = self._get_conversation(user.id, conversation_id)
        if conv is None:
            raise ValidationError(f"Conversation {conversation_id} not found")
        for message in list(conv.messages):
            self._db.delete(message)
        conv.thread_id = str(uuid.uuid4())
        conv.updated_at = datetime.now(timezone.utc)
        self._db.commit()
        self._db.refresh(conv)
        return EmotionalConversationResponse(
            conversation_id=conv.id,
            thread_id=conv.thread_id,
            agent=conv.agent_name,
            messages=[],
            total_count=0,
            has_more=False,
        )

    # ------------------------------------------------------------------
    # Delete a conversation entirely
    # ------------------------------------------------------------------

    async def delete_conversation(
        self, user: User, *, conversation_id: int
    ) -> None:
        conv = self._db.scalar(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user.id,
            )
        )
        if conv is None:
            raise ValidationError(f"Conversation {conversation_id} not found")
        self._db.delete(conv)
        self._db.commit()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _auto_title(conversation: Conversation, first_message: str) -> None:
        """Auto-title a conversation from the first user message if title is default."""
        if conversation.title == "新对话" and first_message:
            # Truncate to ~20 chars for a clean title
            title = first_message.strip()[:20]
            if len(first_message) > 20:
                title += "…"
            conversation.title = title

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
