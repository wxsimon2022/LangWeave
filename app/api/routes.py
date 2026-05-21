"""Compatibility module for legacy intent route imports."""

from app.api.intent_routes import intent_chat, recognize_intent, router

__all__ = ["router", "recognize_intent", "intent_chat"]
