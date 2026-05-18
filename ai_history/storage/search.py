"""Search over the v2 SQLite store (issue #34).

Before this, `load_index()` read the v2 store but the `/search` routes and
the MCP `search_history` tool read a *separate* legacy `index.sqlite` FTS
database — the two could disagree on which sessions exist and on titles.

`search_sessions` queries v2's unified `search_index` FTS5 table, which is
populated by `storage.writer` from the same data `load_index_v2` serves —
so search and the session list are now consistent by construction.

Returns the same ``[{"session": <dict>, "score": <float>}]`` shape the
legacy ``SearchEngine.search`` produced, so callers need no changes.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from .reader import _row_to_session_dict
from .schema import open_connection
from .writer import v2_db_path


def search_sessions(
    output_dir: Path,
    query: str,
    *,
    tool: Optional[str] = None,
    project: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Full-text search sessions in the v2 store.

    Args:
        output_dir: directory holding ``index_v2.sqlite``.
        query: free-text query; terms are prefix-matched.
        tool: optional exact tool filter.
        project: optional substring project filter.
        limit: max results.

    Returns:
        ``[{"session": <legacy session dict>, "score": <float>}]`` ordered
        best-match-first. Empty list when the v2 store is absent, the query
        is too short, or the FTS expression is malformed.
    """
    db = v2_db_path(output_dir)
    if not db.exists():
        return []

    terms = [t for t in (query or "").split() if t]
    if not terms:
        return []
    # Prefix-match each term; double-quote to neutralise FTS operators.
    fts_query = " ".join(f'"{t}"*' for t in terms)

    conn = open_connection(db)
    try:
        rows = conn.execute(
            """
            SELECT s.id, s.tool, s.project, s.thread_id, s.title,
                   s.created, s.updated, s.source_path, s.source_mtime_ns,
                   s.git_branch, s.git_commit, s.metadata_json,
                   s.messages_count, s.prompt_count, s.prompt_outline,
                   s.export_path,
                   bm25(search_index) AS score
            FROM search_index
            JOIN sessions s ON s.id = search_index.entity_id
            WHERE search_index MATCH ?
              AND search_index.entity_type = 'session'
            ORDER BY score ASC
            LIMIT ?
            """,
            (fts_query, max(1, limit) * 4),
        ).fetchall()
    except sqlite3.Error:
        return []
    finally:
        conn.close()

    results: List[Dict[str, Any]] = []
    for row in rows:
        session = _row_to_session_dict(row)
        if tool and session.get("tool") != tool:
            continue
        if project and project not in str(session.get("project") or ""):
            continue
        results.append({"session": session, "score": float(row["score"])})
        if len(results) >= limit:
            break
    return results
