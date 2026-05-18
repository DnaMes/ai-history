"""v2 SQLite schema + migration runner (issue #44).

The schema is built up from a list of numbered, append-only migrations.
Each migration is one or more SQL statements; the runner records applied
versions in ``schema_version`` and skips anything already applied. This
keeps existing databases upgradeable forever and lets tests assert any
specific version.

Tier 1 — sessions and their messages (this PR).
Tier 2 — memory tables for agent-written knowledge (lands in PR 4).
Tier 3 — memory_sources linking memory back to the sessions it came from.

The unified FTS5 ``search_index`` covers Tier 1 from day one and gains
Tier 2/3 rows later without a schema change.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple

# (version, description, sql) — append new migrations, NEVER edit existing ones.
MIGRATIONS: List[Tuple[int, str, str]] = [
    (
        1,
        "schema_version bookkeeping table",
        """
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            description TEXT NOT NULL,
            applied_at TEXT NOT NULL
        );
        """,
    ),
    (
        2,
        "tier 1: sessions table",
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id            TEXT PRIMARY KEY,
            tool          TEXT NOT NULL,
            project       TEXT,
            thread_id     TEXT,
            title         TEXT,
            created       TEXT NOT NULL,
            updated       TEXT NOT NULL,
            source_path   TEXT,
            source_mtime_ns INTEGER,
            git_branch    TEXT,
            git_commit    TEXT,
            cli_version   TEXT,
            metadata_json TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_sessions_tool      ON sessions(tool);
        CREATE INDEX IF NOT EXISTS idx_sessions_project   ON sessions(project);
        CREATE INDEX IF NOT EXISTS idx_sessions_thread    ON sessions(thread_id);
        CREATE INDEX IF NOT EXISTS idx_sessions_updated   ON sessions(updated DESC);
        """,
    ),
    (
        3,
        "tier 1: messages table",
        """
        CREATE TABLE IF NOT EXISTS messages (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT    NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
            seq        INTEGER NOT NULL,
            role       TEXT    NOT NULL,
            content    TEXT    NOT NULL,
            timestamp  TEXT,
            model      TEXT,
            tokens_json TEXT,
            UNIQUE(session_id, seq)
        );
        CREATE INDEX IF NOT EXISTS idx_messages_session  ON messages(session_id);
        CREATE INDEX IF NOT EXISTS idx_messages_role     ON messages(role);
        CREATE INDEX IF NOT EXISTS idx_messages_session_seq
            ON messages(session_id, seq);
        """,
    ),
    (
        4,
        "unified FTS5 search index (sessions + messages today, memory in PR4)",
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5(
            entity_type UNINDEXED,   -- 'session' | 'message' | 'memory' (PR4)
            entity_id   UNINDEXED,   -- TEXT id (sessions) or rowid (messages, memory)
            tool        UNINDEXED,
            project     UNINDEXED,
            title,
            body,
            tokenize='porter unicode61'
        );
        """,
    ),
    (
        5,
        "deletion tombstones (replaces the deleted_sessions.json file)",
        """
        CREATE TABLE IF NOT EXISTS deleted_sessions (
            session_id TEXT PRIMARY KEY,
            deleted_at TEXT NOT NULL,
            reason     TEXT
        );
        """,
    ),
    (
        6,
        "denormalised display columns on sessions (avoids count joins on read)",
        """
        ALTER TABLE sessions ADD COLUMN messages_count INTEGER NOT NULL DEFAULT 0;
        ALTER TABLE sessions ADD COLUMN prompt_count   INTEGER NOT NULL DEFAULT 0;
        ALTER TABLE sessions ADD COLUMN prompt_outline TEXT;
        ALTER TABLE sessions ADD COLUMN export_path    TEXT;
        """,
    ),
]


def open_connection(path: Path) -> sqlite3.Connection:
    """Open a connection with PRAGMAs sensible for our workload.

    - ``isolation_level=None`` puts the connection in autocommit mode, which
      we want so that PRAGMAs run immediately and ``executescript()`` can
      contain DDL without colliding with Python's implicit BEGIN. The
      migration runner brackets each step in its own explicit BEGIN/COMMIT.
    - WAL gives concurrent readers + a writer (web UI reads while syncs run).
    - foreign_keys must be enabled per-connection — SQLite default is OFF.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def current_version(conn: sqlite3.Connection) -> int:
    """Return the highest applied migration version (0 on fresh DB)."""
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
    ).fetchone()
    if not row:
        return 0
    result = conn.execute("SELECT COALESCE(MAX(version), 0) FROM schema_version").fetchone()
    return int(result[0])


def apply_migrations(conn: sqlite3.Connection) -> int:
    """Apply every pending migration in order. Returns the new current version.

    Each migration runs inside its own transaction; a failing migration rolls
    back and re-raises, leaving the DB at the last successfully applied
    version. Idempotent — running it twice is a no-op.
    """
    applied = current_version(conn)
    for version, description, sql in MIGRATIONS:
        if version <= applied:
            continue
        # executescript() implicitly issues COMMIT before running, which would
        # close any BEGIN we started here. So: run the DDL first (autocommit),
        # then record the bookkeeping insert in its own short transaction.
        try:
            conn.executescript(sql)
            conn.execute("BEGIN")
            conn.execute(
                "INSERT INTO schema_version(version, description, applied_at) " "VALUES (?, ?, ?)",
                (
                    version,
                    description,
                    datetime.now(timezone.utc).isoformat(timespec="seconds"),
                ),
            )
            conn.execute("COMMIT")
        except sqlite3.Error:
            # Best-effort rollback; if no tx is open this is a noop in autocommit.
            try:
                conn.execute("ROLLBACK")
            except sqlite3.OperationalError:
                pass
            raise
        applied = version
    return applied


# Public helper for callers that want a ready-to-use DB in one call.
def initialise(path: Path) -> sqlite3.Connection:
    """Open ``path`` and apply every pending migration. Returns the connection."""
    conn = open_connection(path)
    apply_migrations(conn)
    return conn
