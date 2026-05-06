#!/usr/bin/env python3
"""CLI entry point for the ai-history MCP server."""

import asyncio
import sys
from pathlib import Path

# Add local package to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ai_history.interfaces.mcp import create_server


async def main():
    """Run the MCP server over stdio."""
    server = create_server()
    await server.run()


def main_sync():
    """Synchronous script wrapper for setuptools entry points."""
    asyncio.run(main())


if __name__ == "__main__":
    main_sync()
