"""``lore-web`` entry point — serve the Lore web UI.

This is a thin CLI wrapper around :func:`lore.interfaces.web.start_web_ui`. It is
intended for local/dev use; in production the app is served by gunicorn
(``lore.interfaces.web:app``) — see the Dockerfile.
"""

from __future__ import annotations

import argparse
import os


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lore-web",
        description="Serve the Lore web UI (Flask dev server). For production use gunicorn.",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("LORE_WEB_HOST", "127.0.0.1"),
        help="Bind host (default 127.0.0.1, or $LORE_WEB_HOST).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("LORE_WEB_PORT", "5000")),
        help="Bind port (default 5000, or $LORE_WEB_PORT).",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        default=os.environ.get("LORE_WEB_DEBUG", "").lower() == "true",
        help="Run Flask in debug mode (or set $LORE_WEB_DEBUG=true).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    # Imported lazily so `--help` doesn't pay the heavy web.py import cost.
    from lore.interfaces.web import start_web_ui

    start_web_ui(port=args.port, host=args.host, debug=args.debug)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
