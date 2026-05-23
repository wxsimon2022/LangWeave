"""MCP server configuration — placeholder."""
from __future__ import annotations

from pydantic import BaseModel


class MCPServerConfig(BaseModel):
    """Configuration for an MCP server."""
    name: str = ""
    url: str = ""
    api_key: str = ""
