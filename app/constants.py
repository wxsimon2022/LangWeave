"""Shared constants for the application."""

from __future__ import annotations

# Agent names
INTENT_AGENT = "intent"
ASSISTANT_AGENT = "assistant"
EMOTIONAL_AGENT = "emotional"
DEFAULT_TARGET_AGENT = ASSISTANT_AGENT

# Agent descriptions
INTENT_DESCRIPTION = "Classifies user intent via structured output"
ASSISTANT_DESCRIPTION = "General assistant with calculator and clock tools"
EMOTIONAL_DESCRIPTION = "情感陪伴与倾听，提供共情式对话支持（支持多轮记忆）"

# Database
DEFAULT_AGENT_NAME = EMOTIONAL_AGENT

# JWT
JWT_ALGORITHM = "HS256"
PBKDF2_ITERATIONS = 390000
DEFAULT_JWT_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# CORS
DEFAULT_CORS_ORIGINS = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:5174",
    "http://localhost:5174",
]

# API
API_V1_PREFIX = "/api/v1"
API_V1_AUTH = f"{API_V1_PREFIX}/auth"
API_V1_EMOTIONAL_CHAT = f"{API_V1_PREFIX}/emotional-chat"
API_V1_INTENT = f"{API_V1_PREFIX}/intent"
API_V1_SESSIONS = f"{API_V1_PREFIX}/sessions"
