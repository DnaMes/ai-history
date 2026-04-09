#!/usr/bin/env python3
import sys
import os
from pathlib import Path

# Add local package to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ai_history.interfaces.web import app, start_web_ui


def main():
    host = os.environ.get("FLASK_HOST", "127.0.0.1")
    port = int(os.environ.get("FLASK_PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    start_web_ui(host=host, port=port, debug=debug)


if __name__ == "__main__":
    main()
