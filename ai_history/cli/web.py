#!/usr/bin/env python3
"""CLI entry point for the ai-history web UI."""

from __future__ import annotations

import os

from ai_history.interfaces.web import start_web_ui


def main() -> None:
    host = os.environ.get("FLASK_HOST", "127.0.0.1")
    port = int(os.environ.get("FLASK_PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    start_web_ui(host=host, port=port, debug=debug)


if __name__ == "__main__":
    main()
