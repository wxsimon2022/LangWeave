"""Compatibility module for HTTP dependencies."""

from app.interfaces.http.deps import get_intent_service, get_session_service

__all__ = ["get_intent_service", "get_session_service"]
