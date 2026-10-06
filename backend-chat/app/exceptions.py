"""Application-specific exceptions.

Every exception carries an optional ``code`` string that the HTTP layer
maps to the ``{code, message, data}`` response envelope (see
``langweave.web.response.ApiResponse``).
"""

from __future__ import annotations


class AppError(Exception):
    """Base exception for all application errors.

    Subclass this instead of ``Exception`` directly so that the global
    error handler can catch everything under a single type.
    """

    def __init__(self, message: str, code: str | None = None) -> None:
        self.message = message
        self.code = code
        super().__init__(self.message)


class AuthenticationError(AppError):
    """JWT validation or session check failed.

    Raised by ``app.interfaces.http.deps.get_current_user`` when
    the token is missing, expired, revoked, or superseded by a
    newer login.
    """

    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(message, code="AUTH_ERROR")


class AgentNotFoundError(AppError):
    """Agent name does not exist in the registry.

    Raised by ``ChatService._get_agent`` when a conversation has a
    ``agent_name`` that was never registered (e.g. after a config change).
    """

    def __init__(self, agent_name: str) -> None:
        super().__init__(f"Unknown agent: {agent_name}", code="AGENT_NOT_FOUND")


class ValidationError(AppError):
    """Input validation failed at the application / service layer.

    Distinct from FastAPI's ``RequestValidationError`` — this is for
    business-rule violations that Pydantic field constraints cannot express.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message, code="VALIDATION_ERROR")


class ServiceError(AppError):
    """Generic service operation failure.

    Used when a lower-level error (DB timeout, external API failure)
    needs to be surfaced with a specific code.
    """

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message, code=code or "SERVICE_ERROR")
