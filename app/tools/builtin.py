"""Compose framework tools and business tools for agents."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from langchain_core.tools import BaseTool

from langweave.tools import calculator, current_time

from app.tools.order import query_order_status


def get_default_tools() -> list[BaseTool | Any]:
    """Tools exposed to the default assistant agent."""
    return [calculator, current_time, query_order_status]
