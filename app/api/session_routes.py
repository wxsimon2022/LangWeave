"""Compatibility module for session HTTP routes."""

from app.interfaces.http.session_routes import clear_session, get_session_history, router

__all__ = ["router", "get_session_history", "clear_session"]
