"""HTTP request/response schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User message")
    thread_id: str | None = Field(
        default=None,
        description="Conversation thread id for checkpointer-backed sessions",
    )


class ChatResponse(BaseModel):
    content: str
    agent: str
    thread_id: str | None = None


class InvokeRequest(BaseModel):
    """Full agent invoke; accepts a single message or LangGraph state dict."""

    message: str | None = Field(
        default=None,
        description="Shortcut: wraps into messages as HumanMessage",
    )
    input: dict[str, Any] | None = Field(
        default=None,
        description="Raw LangGraph input, e.g. {\"messages\": [...]}",
    )
    thread_id: str | None = None

    def to_agent_input(self) -> str | dict[str, Any]:
        if self.input is not None:
            return self.input
        if self.message is not None:
            return self.message
        msg = "Either 'message' or 'input' is required"
        raise ValueError(msg)


class InvokeResponse(BaseModel):
    agent: str
    thread_id: str | None = None
    state: dict[str, Any]


class StreamRequest(BaseModel):
    message: str = Field(..., min_length=1)
    thread_id: str | None = None
    stream_mode: str | list[str] = "updates"


class AgentInfo(BaseModel):
    name: str
    description: str = ""


class AgentListResponse(BaseModel):
    agents: list[AgentInfo]
