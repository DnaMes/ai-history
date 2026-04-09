#!/usr/bin/env python3
"""
ai-history MCP Server

A Model Context Protocol server that provides AI chat history search and retrieval
capabilities to AI coding assistants like Claude Code, Cursor, and Gemini CLI.

Usage:
    python3 ai-history-mcp.py

Configure in Claude Code (~/.claude/settings.json):
    {
      "mcpServers": {
        "ai-history": {
          "command": "python3",
          "args": ["/path/to/ai-history-mcp.py"]
        }
      }
    }
"""

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
