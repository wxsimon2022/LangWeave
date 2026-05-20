"""Serialize agent state for JSON responses."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import BaseMessage


def serialize_messages(messages: list[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for msg in messages:
        if isinstance(msg, BaseMessage):
            out.append(msg.model_dump())
        elif isinstance(msg, dict):
            out.append(msg)
        else:
            out.append({"content": str(msg)})
    return out


def serialize_state(state: dict[str, Any]) -> dict[str, Any]:
    result = dict(state)
    if "messages" in result:
        result["messages"] = serialize_messages(result["messages"])
    if "structured_response" in result and hasattr(
        result["structured_response"], "model_dump"
    ):
        result["structured_response"] = result["structured_response"].model_dump()
    return result


def json_dumps(obj: Any) -> str:
    return json.dumps(obj, default=_json_default, ensure_ascii=False)


def _json_default(obj: Any) -> Any:
    if isinstance(obj, BaseMessage):
        return obj.model_dump()
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    return str(obj)
