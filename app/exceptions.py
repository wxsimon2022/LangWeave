"""Application-specific exceptions."""

from __future__ import annotations


class AppError(Exception):
    """Base exception for application errors."""

    def __init__(self, message: str, code: str | None = None) -> None:
        self.message = message
        self.code = code
        super().__init__(self.message)


class AuthenticationError(AppError):
    """Authentication failed."""

    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(message, code="AUTH_ERROR")


class AgentNotFoundError(AppError):
    """Agent not found in registry."""

    def __init__(self, agent_name: str) -> None:
        super().__init__(f"Unknown agent: {agent_name}", code="AGENT_NOT_FOUND")


class ValidationError(AppError):
    """Input validation failed."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="VALIDATION_ERROR")


class ServiceError(AppError):
    """Service operation failed."""

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message, code=code or "SERVICE_ERROR")
