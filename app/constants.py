"""Shared constants for the application.

Agent naming, JWT parameters, CORS origins and API path prefixes
live here so every module reads from a single source of truth.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Agent names and descriptions
# The three agents form an "entry → specialist" pattern: the ``intent``
# agent classifies the first message in each conversation, then routes to
# ``assistant`` or ``emotional`` for the actual reply.
# ---------------------------------------------------------------------------

INTENT_AGENT = "intent"              # Classifies user intent (structured output)
ASSISTANT_AGENT = "assistant"        # General helper w/ calculator, clock tools
EMOTIONAL_AGENT = "emotional"        # Empathetic companion (小暖)
DEFAULT_TARGET_AGENT = ASSISTANT_AGENT  # Fallback when intent is unknown

INTENT_DESCRIPTION = "Classifies user intent via structured output"
ASSISTANT_DESCRIPTION = "General assistant with calculator and clock tools"
EMOTIONAL_DESCRIPTION = "情感陪伴与倾听，提供共情式对话支持（支持多轮记忆）"

# New conversations default to the emotional agent; the intent classifier
# re-routes after the first message if needed.
DEFAULT_AGENT_NAME = EMOTIONAL_AGENT

# ---------------------------------------------------------------------------
# JWT / Auth
# PBKDF2_ITERATIONS = 390_000 is the OWASP 2023 recommended minimum for
# PBKDF2-HMAC-SHA256.  Increase as hardware improves.
# ---------------------------------------------------------------------------

JWT_ALGORITHM = "HS256"
PBKDF2_ITERATIONS = 390000
DEFAULT_JWT_EXPIRE_MINUTES = 60 * 2  # 2 hours

# ---------------------------------------------------------------------------
# CORS — dev frontends on Vite default ports
# ---------------------------------------------------------------------------

DEFAULT_CORS_ORIGINS = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:5174",
    "http://localhost:5174",
]

# ---------------------------------------------------------------------------
# API path prefixes — change here to version the entire surface
# ---------------------------------------------------------------------------

API_V1_PREFIX = "/api/v1"
API_V1_AUTH = f"{API_V1_PREFIX}/auth"
API_V1_SESSIONS = f"{API_V1_PREFIX}/sessions"
API_V1_CONVERSATIONS = f"{API_V1_PREFIX}/conversations"
API_V1_UNIFIED_STREAM = f"{API_V1_PREFIX}/unified/stream"

# Redis key namespace — all cache keys share this prefix for
# simple partitioning in a shared Redis instance.
REDIS_KEY_PREFIX = "chat:"
