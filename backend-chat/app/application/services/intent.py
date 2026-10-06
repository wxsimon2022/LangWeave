"""Intent recognition and agent routing."""

from __future__ import annotations

import json
import re
from typing import Any

from langweave.agent import Agent
from langweave.registry import AgentRegistry

from app.schemas.intent import IntentChatResponse, UserIntent
from app.exceptions import AgentNotFoundError, ValidationError
from app.constants import INTENT_AGENT, DEFAULT_TARGET_AGENT


class IntentService:
    """Call the intent agent, parse structured output, optionally route to workers."""

    def __init__(self, registry: AgentRegistry) -> None:
        self._registry = registry

    async def recognize(
        self,
        message: str,
        *,
        thread_id: str | None = None,
    ) -> UserIntent:
        message = message.strip()
        if not message:
            raise ValidationError("Message cannot be empty")

        agent = self._get_intent_agent()
        result = await agent.ainvoke(message, thread_id=thread_id)
        return self._parse_result(result)

    async def recognize_and_chat(
        self,
        message: str,
        *,
        thread_id: str | None = None,
        auto_reply: bool = True,
    ) -> IntentChatResponse:
        intent = await self.recognize(message, thread_id=thread_id)
        if not auto_reply:
            return IntentChatResponse(intent=intent, thread_id=thread_id)

        target = intent.target_agent or DEFAULT_TARGET_AGENT
        worker = self._get_agent(target)
        enriched = self._build_worker_message(message, intent)
        reply, _ = await worker.achat(enriched, thread_id=thread_id)
        return IntentChatResponse(
            intent=intent,
            reply=reply,
            agent=target,
            thread_id=thread_id,
        )

    def _get_intent_agent(self) -> Agent:
        return self._get_agent(INTENT_AGENT)

    def _get_agent(self, name: str) -> Agent:
        try:
            return self._registry.get(name)
        except KeyError as exc:
            raise AgentNotFoundError(name) from exc

    def _parse_result(self, result: dict[str, Any]) -> UserIntent:
        structured = result.get("structured_response")
        if isinstance(structured, UserIntent):
            return structured
        if isinstance(structured, dict):
            return UserIntent.model_validate(structured)

        for msg in reversed(result.get("messages", [])):
            content = getattr(msg, "content", None)
            if not content:
                continue
            text = content if isinstance(content, str) else ""
            parsed = self._parse_json_from_text(text)
            if parsed is not None:
                return UserIntent.model_validate(parsed)

        return UserIntent(
            intent="unknown",
            confidence=0.0,
            slots={},
            target_agent=DEFAULT_TARGET_AGENT,
            reasoning="Failed to parse structured intent from model response",
        )

    @staticmethod
    def _parse_json_from_text(text: str) -> dict[str, Any] | None:
        text = text.strip()
        try:
            data = json.loads(text)
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            pass
        match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
                return data if isinstance(data, dict) else None
            except json.JSONDecodeError:
                pass
        return None

    @staticmethod
    def _build_worker_message(user_message: str, intent: UserIntent) -> str:
        """Give the worker agent context from intent classification."""
        slots_txt = json.dumps(intent.slots, ensure_ascii=False)
        return (
            f"[intent={intent.intent}, confidence={intent.confidence}, slots={slots_txt}]\n"
            f"用户说：{user_message}"
        )
