"""Agent memory — the write/recall API for the shared knowledge store (#44 PR 4).

This is the heart of the vision: a place where humans *and* agents record
durable knowledge (facts, decisions, lessons, snippets) that any tool can
later recall. Memory lives in the same v2 SQLite database as the extracted
sessions, and shares the unified ``search_index`` FTS table — so one query
surfaces both past sessions and recorded memory.

Design notes:
- Memory is *append-and-supersede*, not edit-in-place: updating a memory
  inserts a new row and points the old one's ``superseded_by`` at it. This
  keeps an audit trail — you can always see what an agent used to believe.
- ``scope_project`` / ``scope_tool`` let a memory be global or narrowed.
- Every memory gets a row in ``search_index`` (entity_type='memory') so it
  is found by the same search that finds sessions.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .schema import initialise
from .writer import v2_db_path

# Recognised memory kinds. Not enforced as a CHECK constraint (forward-compat)
# but the API validates against this set.
MEMORY_KINDS = ("fact", "decision", "todo", "snippet", "link", "lesson", "note")


@dataclass
class MemoryEntry:
    """One recalled memory row."""

    id: int
    kind: str
    title: str
    body: str
    author: Optional[str]
    created: str
    updated: str
    scope_project: Optional[str] = None
    scope_tool: Optional[str] = None
    superseded_by: Optional[int] = None
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "title": self.title,
            "body": self.body,
            "author": self.author,
            "created": self.created,
            "updated": self.updated,
            "scope_project": self.scope_project,
            "scope_tool": self.scope_tool,
            "superseded_by": self.superseded_by,
            "tags": self.tags,
        }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _connect(output_dir: Path) -> sqlite3.Connection:
    """Open the v2 DB (creating + migrating it if needed) for memory ops."""
    conn = initialise(v2_db_path(output_dir))
    conn.row_factory = sqlite3.Row
    return conn


def add_memory(
    output_dir: Path,
    kind: str,
    title: str,
    body: str,
    *,
    author: str = "human",
    scope_project: Optional[str] = None,
    scope_tool: Optional[str] = None,
    tags: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> int:
    """Record a new memory and index it for search. Returns the new memory id.

    Raises:
        ValueError: if ``kind`` is unknown or ``title``/``body`` are empty.
    """
    if kind not in MEMORY_KINDS:
        raise ValueError(f"unknown memory kind {kind!r}; expected one of {MEMORY_KINDS}")
    title = (title or "").strip()
    body = (body or "").strip()
    if not title:
        raise ValueError("memory title must not be empty")
    if not body:
        raise ValueError("memory body must not be empty")

    now = _now()
    conn = _connect(output_dir)
    try:
        conn.execute("BEGIN")
        cur = conn.execute(
            """
            INSERT INTO memory (
                kind, title, body, scope_project, scope_tool, author,
                created, updated, superseded_by, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?)
            """,
            (
                kind,
                title,
                body,
                scope_project,
                scope_tool,
                author,
                now,
                now,
                json.dumps(metadata, ensure_ascii=False) if metadata else None,
            ),
        )
        memory_id = int(cur.lastrowid or 0)

        for tag in {t.strip() for t in (tags or []) if t and t.strip()}:
            conn.execute(
                "INSERT OR IGNORE INTO memory_tags (memory_id, tag) VALUES (?, ?)",
                (memory_id, tag),
            )

        conn.execute(
            """
            INSERT INTO search_index (entity_type, entity_id, tool, project, title, body)
            VALUES ('memory', ?, ?, ?, ?, ?)
            """,
            (str(memory_id), scope_tool or "", scope_project or "", title, body),
        )
        conn.execute("COMMIT")
        return memory_id
    except sqlite3.Error:
        try:
            conn.execute("ROLLBACK")
        except sqlite3.OperationalError:
            pass
        raise
    finally:
        conn.close()


def _load_tags(conn: sqlite3.Connection, memory_id: int) -> List[str]:
    rows = conn.execute(
        "SELECT tag FROM memory_tags WHERE memory_id = ? ORDER BY tag", (memory_id,)
    ).fetchall()
    return [r["tag"] for r in rows]


def _row_to_entry(conn: sqlite3.Connection, row: sqlite3.Row) -> MemoryEntry:
    return MemoryEntry(
        id=row["id"],
        kind=row["kind"],
        title=row["title"],
        body=row["body"],
        author=row["author"],
        created=row["created"],
        updated=row["updated"],
        scope_project=row["scope_project"],
        scope_tool=row["scope_tool"],
        superseded_by=row["superseded_by"],
        tags=_load_tags(conn, row["id"]),
    )


def get_memory(output_dir: Path, memory_id: int) -> Optional[MemoryEntry]:
    """Return a single memory by id, or None if it does not exist."""
    conn = _connect(output_dir)
    try:
        row = conn.execute("SELECT * FROM memory WHERE id = ?", (memory_id,)).fetchone()
        return _row_to_entry(conn, row) if row else None
    finally:
        conn.close()


def list_memory(
    output_dir: Path,
    *,
    kind: Optional[str] = None,
    scope_project: Optional[str] = None,
    include_superseded: bool = False,
    limit: int = 50,
) -> List[MemoryEntry]:
    """List memory entries, newest first, with optional filters."""
    clauses: List[str] = []
    params: List[Any] = []
    if kind:
        clauses.append("kind = ?")
        params.append(kind)
    if scope_project:
        clauses.append("scope_project = ?")
        params.append(scope_project)
    if not include_superseded:
        clauses.append("superseded_by IS NULL")
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""

    conn = _connect(output_dir)
    try:
        # id DESC is the tiebreaker — timestamps are second-resolution, so
        # two memories added in the same second must still order by insertion.
        rows = conn.execute(
            f"SELECT * FROM memory{where} ORDER BY updated DESC, id DESC LIMIT ?",
            (*params, max(1, limit)),
        ).fetchall()
        return [_row_to_entry(conn, r) for r in rows]
    finally:
        conn.close()


def recall_memory(
    output_dir: Path,
    query: str,
    *,
    kind: Optional[str] = None,
    scope_project: Optional[str] = None,
    include_superseded: bool = False,
    limit: int = 10,
) -> List[MemoryEntry]:
    """Full-text search over recorded memory.

    Uses the shared ``search_index`` FTS table (entity_type='memory'). An
    empty/short query falls back to :func:`list_memory` so callers always
    get the most relevant entries.
    """
    terms = [t for t in (query or "").split() if t]
    if not terms:
        return list_memory(
            output_dir,
            kind=kind,
            scope_project=scope_project,
            include_superseded=include_superseded,
            limit=limit,
        )
    # Prefix-match each term ("oauth" should also find "OAuth2"): FTS5's
    # unicode61 tokenizer keeps digits in a token, so an exact match would
    # miss them. Double-quote to neutralise FTS operator characters.
    fts_query = " ".join(f'"{t}"*' for t in terms)

    conn = _connect(output_dir)
    try:
        rows = conn.execute(
            """
            SELECT m.*, bm25(search_index) AS score
            FROM search_index
            JOIN memory m ON m.id = CAST(search_index.entity_id AS INTEGER)
            WHERE search_index MATCH ?
              AND search_index.entity_type = 'memory'
            ORDER BY score ASC
            LIMIT ?
            """,
            (fts_query, max(1, limit) * 4),
        ).fetchall()

        entries: List[MemoryEntry] = []
        for row in rows:
            if kind and row["kind"] != kind:
                continue
            if scope_project and row["scope_project"] != scope_project:
                continue
            if not include_superseded and row["superseded_by"] is not None:
                continue
            entries.append(_row_to_entry(conn, row))
            if len(entries) >= limit:
                break
        return entries
    except sqlite3.Error:
        return []
    finally:
        conn.close()


def supersede_memory(
    output_dir: Path,
    old_id: int,
    title: str,
    body: str,
    *,
    author: str = "human",
    tags: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> int:
    """Replace a memory with an updated version, preserving the audit trail.

    Inserts a new memory (same kind/scope as the old one) and points the old
    row's ``superseded_by`` at it. Returns the new memory id.

    Raises:
        ValueError: if ``old_id`` does not exist.
    """
    old = get_memory(output_dir, old_id)
    if old is None:
        raise ValueError(f"memory {old_id} does not exist")

    new_id = add_memory(
        output_dir,
        kind=old.kind,
        title=title,
        body=body,
        author=author,
        scope_project=old.scope_project,
        scope_tool=old.scope_tool,
        tags=tags if tags is not None else old.tags,
        metadata=metadata,
    )

    conn = _connect(output_dir)
    try:
        conn.execute("BEGIN")
        conn.execute(
            "UPDATE memory SET superseded_by = ?, updated = ? WHERE id = ?",
            (new_id, _now(), old_id),
        )
        conn.execute("COMMIT")
    except sqlite3.Error:
        try:
            conn.execute("ROLLBACK")
        except sqlite3.OperationalError:
            pass
        raise
    finally:
        conn.close()
    return new_id


def link_memory_to_session(
    output_dir: Path,
    memory_id: int,
    session_id: str,
    *,
    message_id: Optional[int] = None,
    note: Optional[str] = None,
) -> None:
    """Record that a memory originated from a particular session/message."""
    conn = _connect(output_dir)
    try:
        conn.execute(
            """
            INSERT OR IGNORE INTO memory_sources (memory_id, session_id, message_id, note)
            VALUES (?, ?, ?, ?)
            """,
            (memory_id, session_id, message_id, note),
        )
    finally:
        conn.close()


def delete_memory(output_dir: Path, memory_id: int) -> bool:
    """Hard-delete a memory and its FTS/tag/source rows. Returns True if removed."""
    conn = _connect(output_dir)
    try:
        conn.execute("BEGIN")
        cur = conn.execute("DELETE FROM memory WHERE id = ?", (memory_id,))
        conn.execute(
            "DELETE FROM search_index WHERE entity_type = 'memory' AND entity_id = ?",
            (str(memory_id),),
        )
        conn.execute("COMMIT")
        return cur.rowcount > 0
    except sqlite3.Error:
        try:
            conn.execute("ROLLBACK")
        except sqlite3.OperationalError:
            pass
        raise
    finally:
        conn.close()
