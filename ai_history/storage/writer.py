"""Write UnifiedSession objects into the v2 SQLite store (issue #44, PR 2).

This is the *dual-write* stage: ``IndexBuilder`` keeps producing the legacy
``index.json`` + ``index.sqlite`` exactly as before and additionally calls
:func:`write_sessions` here to mirror the same data into the v2 schema
(``index_v2.sqlite``). Nothing reads v2 yet — PR 3 flips the readers over.

The write is a full replace inside one transaction: the v2 DB always
reflects the set of sessions handed in, so a rebuild stays consistent.
Callers treat failures here as non-fatal — a v2 write error must never
break the legacy index path.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path
from typing import Dict, Iterable, Optional

from ..core.models import UnifiedSession
from .schema import initialise

logger = logging.getLogger(__name__)

# v2 DB lives beside the legacy index.sqlite until PR 3 promotes it.
V2_DB_NAME = "index_v2.sqlite"


def v2_db_path(output_dir: Path) -> Path:
    """Return the canonical v2 SQLite path for an output directory."""
    return output_dir / V2_DB_NAME


def _session_metadata_json(session: UnifiedSession) -> Optional[str]:
    """Serialise the loose extras that don't get their own column."""
    extras = {}
    if session.summary:
        extras["summary"] = session.summary
    if session.todos:
        extras["todos"] = session.todos
    if session.title_source is not None:
        extras["title_source"] = getattr(session.title_source, "value", str(session.title_source))
    return json.dumps(extras, ensure_ascii=False) if extras else None


def _source_mtime_ns(source_path: Optional[str]) -> Optional[int]:
    if not source_path:
        return None
    try:
        import os

        return os.stat(source_path).st_mtime_ns
    except OSError:
        return None


def _write_reused_entry(conn: sqlite3.Connection, entry: Dict) -> None:
    """Write a metadata-only row from a pre-built index dict.

    Incremental sync hands the IndexBuilder pre-built dicts for unchanged
    sessions instead of re-extracting them — so we have no UnifiedMessage
    objects for those. We still mirror their metadata + search_text into v2
    so the store stays complete; messages for these sessions are simply
    absent until the next full rebuild. (PR 3+ can backfill if needed.)
    """
    session_id = entry.get("id")
    if not session_id:
        return
    title = entry.get("title") or ""
    conn.execute(
        """
        INSERT INTO sessions (
            id, tool, project, thread_id, title, created, updated,
            source_path, source_mtime_ns, git_branch, git_commit,
            cli_version, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            entry.get("tool"),
            entry.get("project"),
            entry.get("thread_id"),
            title,
            entry.get("created"),
            entry.get("updated"),
            entry.get("source_path"),
            entry.get("source_mtime"),
            entry.get("git_branch"),
            entry.get("git_commit"),
            None,
            None,
        ),
    )
    conn.execute(
        """
        INSERT INTO search_index (
            entity_type, entity_id, tool, project, title, body
        ) VALUES ('session', ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            entry.get("tool") or "",
            entry.get("project") or "",
            title,
            entry.get("search_text") or "",
        ),
    )


def write_sessions(
    db_path: Path,
    sessions: Iterable[UnifiedSession],
    titles: Optional[Dict[str, str]] = None,
    reused_entries: Optional[Iterable[Dict]] = None,
) -> int:
    """Replace the v2 store's contents with ``sessions`` (+ reused entries).

    Args:
        db_path: path to the v2 SQLite file (see :func:`v2_db_path`).
        sessions: full sessions to persist; their messages are written too.
        titles: optional ``{session_id: inferred_title}`` overrides — lets the
            caller reuse the title it already computed for the JSON index
            instead of falling back to ``session.title``.
        reused_entries: pre-built index dicts (from incremental sync) for
            unchanged sessions. Written as metadata-only rows so the v2 store
            stays complete; they carry no message rows.

    Returns:
        The total number of session rows written (full + reused).
    """
    titles = titles or {}
    conn = initialise(db_path)
    try:
        conn.execute("BEGIN")
        # Full replace — ON DELETE CASCADE clears the dependent messages,
        # and search_index rows are rebuilt below.
        conn.execute("DELETE FROM sessions")
        conn.execute("DELETE FROM search_index")

        count = 0
        for entry in reused_entries or []:
            _write_reused_entry(conn, entry)
            count += 1

        for session in sessions:
            count += 1
            title = titles.get(session.session_id) or session.title or ""
            conn.execute(
                """
                INSERT INTO sessions (
                    id, tool, project, thread_id, title, created, updated,
                    source_path, source_mtime_ns, git_branch, git_commit,
                    cli_version, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session.session_id,
                    session.tool.value,
                    session.project_path,
                    session.thread_id,
                    title,
                    session.created_at.isoformat(),
                    session.last_updated.isoformat(),
                    session.source_path,
                    _source_mtime_ns(session.source_path),
                    session.git_branch,
                    session.git_commit,
                    session.cli_version,
                    _session_metadata_json(session),
                ),
            )

            body_parts = [title]
            for seq, message in enumerate(session.messages):
                content = message.content or ""
                role = getattr(message.role, "value", str(message.role))
                conn.execute(
                    """
                    INSERT INTO messages (
                        session_id, seq, role, content, timestamp, model, tokens_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session.session_id,
                        seq,
                        role,
                        content,
                        message.timestamp.isoformat() if message.timestamp else None,
                        message.model,
                        json.dumps(message.tokens) if message.tokens else None,
                    ),
                )
                body_parts.append(content)

            # One FTS row per session: title + concatenated message bodies.
            conn.execute(
                """
                INSERT INTO search_index (
                    entity_type, entity_id, tool, project, title, body
                ) VALUES ('session', ?, ?, ?, ?, ?)
                """,
                (
                    session.session_id,
                    session.tool.value,
                    session.project_path or "",
                    title,
                    "\n".join(p for p in body_parts if p),
                ),
            )

        conn.execute("COMMIT")
        return count
    except sqlite3.Error:
        try:
            conn.execute("ROLLBACK")
        except sqlite3.OperationalError:
            pass
        raise
    finally:
        conn.close()


def write_sessions_safe(
    output_dir: Path,
    sessions: Iterable[UnifiedSession],
    titles: Optional[Dict[str, str]] = None,
    reused_entries: Optional[Iterable[Dict]] = None,
) -> int:
    """Best-effort wrapper used by IndexBuilder's dual-write.

    A failure to mirror data into v2 must never break the legacy index, so
    any exception is logged and swallowed. Returns the count written, or 0
    on failure.
    """
    try:
        return write_sessions(
            v2_db_path(output_dir),
            sessions,
            titles=titles,
            reused_entries=reused_entries,
        )
    except Exception as exc:  # noqa: BLE001 - intentional: v2 write is best-effort
        logger.warning("v2 dual-write skipped (non-fatal): %s", exc)
        return 0
