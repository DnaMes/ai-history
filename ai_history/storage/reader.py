"""Read the v2 SQLite store back into the legacy index dict shape (#44, PR 3).

PR 2 made ``IndexBuilder`` mirror every rebuild into ``index_v2.sqlite``.
This module is the read side: :func:`load_index_v2` returns exactly the
``{"stats": {...}, "sessions": [...]}`` structure that the web layer's
``load_index()`` has always produced from ``index.json`` — so callers need
no changes when the reader is switched over.

Keeping the output shape identical is deliberate: it lets PR 3 flip the
source behind a feature flag with the JSON path as a fallback, and lets PR
3's tests assert v2 and JSON produce equivalent payloads.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List

from .schema import current_version
from .writer import v2_db_path

# A v2 DB is only usable once the denormalised display columns exist (v6).
_MIN_USABLE_VERSION = 6


def v2_is_available(output_dir: Path) -> bool:
    """True if a v2 DB exists and is migrated far enough to read from."""
    db = v2_db_path(output_dir)
    if not db.exists():
        return False
    try:
        conn = sqlite3.connect(str(db))
        try:
            return current_version(conn) >= _MIN_USABLE_VERSION
        finally:
            conn.close()
    except sqlite3.Error:
        return False


def _row_to_session_dict(row: sqlite3.Row) -> Dict[str, Any]:
    """Map one v2 ``sessions`` row to a legacy index session dict."""
    metadata: Dict[str, Any] = {}
    raw_meta = row["metadata_json"]
    if raw_meta:
        try:
            metadata = json.loads(raw_meta)
        except (ValueError, TypeError):
            metadata = {}
    return {
        "id": row["id"],
        "tool": row["tool"],
        "project": row["project"],
        "thread_id": row["thread_id"],
        "title": row["title"],
        "created": row["created"],
        "updated": row["updated"],
        "messages": int(row["messages_count"] or 0),
        "prompts": int(row["prompt_count"] or 0),
        "prompt_outline": row["prompt_outline"],
        "export_path": row["export_path"],
        "git_branch": row["git_branch"],
        "git_commit": row["git_commit"],
        "source_path": row["source_path"],
        "source_mtime": row["source_mtime_ns"],
        "summary": metadata.get("summary"),
    }


def _compute_stats(sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build the legacy ``stats`` block from session dicts."""
    by_tool: Dict[str, int] = {}
    by_project: Dict[str, int] = {}
    total_messages = 0
    for s in sessions:
        tool = str(s.get("tool") or "")
        if tool:
            by_tool[tool] = by_tool.get(tool, 0) + 1
        project = s.get("project")
        if project:
            by_project[project] = by_project.get(project, 0) + 1
        total_messages += int(s.get("messages") or 0)
    return {
        "total_sessions": len(sessions),
        "total_messages": total_messages,
        "by_tool": by_tool,
        "by_project": by_project,
    }


def load_index_v2(output_dir: Path) -> Dict[str, Any]:
    """Load the v2 store as a legacy-shaped index dict.

    Returns ``{"version": "2", "stats": {...}, "sessions": [...]}`` — the same
    structure ``load_index()`` returns from ``index.json``. Sessions are
    sorted newest-first by ``updated``.

    Raises:
        FileNotFoundError: if no v2 DB exists at ``output_dir``.
    """
    db = v2_db_path(output_dir)
    if not db.exists():
        raise FileNotFoundError(f"no v2 store at {db}")

    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT id, tool, project, thread_id, title, created, updated,
                   source_path, source_mtime_ns, git_branch, git_commit,
                   metadata_json, messages_count, prompt_count,
                   prompt_outline, export_path
            FROM sessions
            ORDER BY updated DESC
            """
        ).fetchall()
    finally:
        conn.close()

    sessions = [_row_to_session_dict(r) for r in rows]
    return {
        "version": "2",
        "stats": _compute_stats(sessions),
        "sessions": sessions,
    }
