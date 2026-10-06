"""HTTP request/response schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    """Agent 对话请求体。"""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"message": "你好，介绍一下你自己", "thread_id": "session-001"},
            ]
        }
    )

    message: str = Field(..., min_length=1, description="用户输入文本", examples=["你好"])
    thread_id: str | None = Field(
        default=None,
        description="会话 ID；不传则自动生成。同一 thread_id 可多轮记住上下文",
        examples=["session-001"],
    )


class ChatResponse(BaseModel):
    """Agent 对话响应。"""

    content: str = Field(description="模型回复正文")
    agent: str = Field(description="实际处理的 Agent 名称")
    thread_id: str | None = Field(
        default=None,
        description="会话 ID（多轮记忆）；首次对话未传时会返回新生成的 id",
    )


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
