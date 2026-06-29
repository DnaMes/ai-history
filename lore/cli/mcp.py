#!/usr/bin/env python3
"""``lore-mcp`` entry point — run the Lore MCP server over stdio."""

from __future__ import annotations

import asyncio

from lore.interfaces.mcp import create_server


async def main() -> None:
    """Run the MCP server over stdio."""
    server = create_server()
    await server.run()


def main_sync() -> None:
    """Synchronous script wrapper for setuptools entry points."""
    asyncio.run(main())


if __name__ == "__main__":
    main_sync()
