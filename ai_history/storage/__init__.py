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

from .memory import (
    MEMORY_KINDS,
    MemoryEntry,
    add_memory,
    delete_memory,
    get_memory,
    link_memory_to_session,
    list_memory,
    recall_memory,
    supersede_memory,
)
from .reader import load_index_v2, v2_is_available
from .schema import apply_migrations, current_version, initialise, open_connection
from .writer import v2_db_path, write_sessions, write_sessions_safe

__all__ = [
    "MEMORY_KINDS",
    "MemoryEntry",
    "add_memory",
    "apply_migrations",
    "current_version",
    "delete_memory",
    "get_memory",
    "initialise",
    "link_memory_to_session",
    "list_memory",
    "load_index_v2",
    "open_connection",
    "recall_memory",
    "supersede_memory",
    "v2_db_path",
    "v2_is_available",
    "write_sessions",
    "write_sessions_safe",
]
