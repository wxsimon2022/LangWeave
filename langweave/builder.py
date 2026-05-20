"""Fluent builder for LangChain agents."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware.types import AgentMiddleware, AgentState
from langchain.chat_models import init_chat_model
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import SystemMessage
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.store.base import BaseStore

from langweave.agent import Agent
from langweave.config import AgentSettings


class AgentBuilder:
    """Configure model, tools, middleware, and compile into an `Agent`."""

    def __init__(self, settings: AgentSettings | None = None) -> None:
        self._settings = settings or AgentSettings.from_env()
        self._name: str | None = None
        self._description: str | None = None
        self._model: str | BaseChatModel | None = self._settings.model
        self._model_kwargs: dict[str, Any] = {}
        self._tools: list[BaseTool | Callable[..., Any] | dict[str, Any]] = []
        self._middleware: list[AgentMiddleware[Any, Any, Any]] = []
        self._system_prompt: str | SystemMessage | None = self._settings.system_prompt
        self._response_format: Any = None
        self._state_schema: type[AgentState[Any]] | None = None
        self._context_schema: type[Any] | None = None
        self._checkpointer: BaseCheckpointSaver | None = None
        self._store: BaseStore | None = None
        self._debug: bool = self._settings.debug

    def with_name(self, name: str) -> AgentBuilder:
        self._name = name
        return self

    def with_description(self, description: str) -> AgentBuilder:
        self._description = description
        return self

    def with_model(
        self,
        model: str | BaseChatModel,
        **kwargs: Any,
    ) -> AgentBuilder:
        self._model = model
        self._model_kwargs.update(kwargs)
        return self

    def with_system_prompt(self, prompt: str | SystemMessage) -> AgentBuilder:
        self._system_prompt = prompt
        return self

    def with_tools(
        self,
        tools: Sequence[BaseTool | Callable[..., Any] | dict[str, Any]],
    ) -> AgentBuilder:
        self._tools = list(tools)
        return self

    def add_tool(
        self,
        tool: BaseTool | Callable[..., Any] | dict[str, Any],
    ) -> AgentBuilder:
        self._tools.append(tool)
        return self

    def with_middleware(
        self,
        *middleware: AgentMiddleware[Any, Any, Any],
    ) -> AgentBuilder:
        self._middleware.extend(middleware)
        return self

    def with_response_format(self, response_format: Any) -> AgentBuilder:
        self._response_format = response_format
        return self

    def with_state_schema(
        self,
        schema: type[AgentState[Any]],
    ) -> AgentBuilder:
        self._state_schema = schema
        return self

    def with_context_schema(self, schema: type[Any]) -> AgentBuilder:
        self._context_schema = schema
        return self

    def with_checkpointer(
        self,
        checkpointer: BaseCheckpointSaver,
    ) -> AgentBuilder:
        self._checkpointer = checkpointer
        return self

    def with_store(self, store: BaseStore) -> AgentBuilder:
        self._store = store
        return self

    def with_debug(self, debug: bool = True) -> AgentBuilder:
        self._debug = debug
        return self

    def _resolve_model(self) -> str | BaseChatModel:
        if self._model is None:
            msg = "Model is required. Call with_model() or set LANGWEAVE_MODEL."
            raise ValueError(msg)
        if isinstance(self._model, str):
            return init_chat_model(self._model, **self._model_kwargs)
        return self._model

    def build(self) -> Agent:
        model = self._resolve_model()
        graph = create_agent(
            model,
            self._tools or None,
            system_prompt=self._system_prompt,
            middleware=self._middleware,
            response_format=self._response_format,
            state_schema=self._state_schema,
            context_schema=self._context_schema,
            checkpointer=self._checkpointer,
            store=self._store,
            debug=self._debug,
            name=self._name,
        )
        return Agent(
            graph,
            name=self._name,
            description=self._description,
        )
