"""Agent initialization script."""
from __future__ import annotations

import asyncio

from app.core.app import create_app
from langweave.web.deps import get_registry


async def main() -> None:
    app = create_app()
    registry = get_registry(app)
    print("Registered agents:", registry.list_names())


if __name__ == "__main__":
    asyncio.run(main())
