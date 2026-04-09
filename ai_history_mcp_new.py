#!/usr/bin/env python3
import asyncio
import sys
from pathlib import Path

# Add local package to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ai_history.interfaces.mcp import create_server

async def main():
    server = create_server()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())
