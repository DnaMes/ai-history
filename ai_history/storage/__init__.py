"""Persistent storage layer — SQLite as the single source of truth (issue #44).

This package owns the v2 SQLite schema that supersedes the flat
``index.json`` + parallel ``index.sqlite`` (FTS-only) split. The migration
is staged across multiple PRs:

  PR 1 (this) — Schema + migration runner. No behaviour change yet.
  PR 2       — Dual-write sessions/messages into v2 alongside the JSON index.
  PR 3       — Readers switch to v2; JSON becomes an optional export.
  PR 4       — Memory tables + MCP write/recall tools (the agent-memory vision).

Public surface:
    open_connection(path)  -> sqlite3.Connection
    apply_migrations(conn) -> int   # highest version applied
    current_version(conn)  -> int
"""

from __future__ import annotations

from .reader import load_index_v2, v2_is_available
from .schema import apply_migrations, current_version, initialise, open_connection
from .writer import v2_db_path, write_sessions, write_sessions_safe

__all__ = [
    "apply_migrations",
    "current_version",
    "initialise",
    "load_index_v2",
    "open_connection",
    "v2_db_path",
    "v2_is_available",
    "write_sessions",
    "write_sessions_safe",
]
