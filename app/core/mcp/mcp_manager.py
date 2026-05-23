"""MCP service manager — placeholder."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class MCPManager:
    """Manage MCP server connections and lifecycle."""

    def __init__(self) -> None:
        self._servers: dict[str, dict] = {}

    async def start(self) -> None:
        logger.info("MCPManager started (no servers configured)")

    async def shutdown(self) -> None:
        self._servers.clear()
