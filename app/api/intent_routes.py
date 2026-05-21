"""Compatibility module for intent HTTP routes."""

from app.interfaces.http.intent_routes import intent_chat, recognize_intent, router

__all__ = ["router", "recognize_intent", "intent_chat"]
