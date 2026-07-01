"""Populate per-session embedding vectors for hybrid search (#87, PR 2).

One vector per session, stored in the ``session_embeddings`` vec0 table
(created by :func:`lore.storage.schema.ensure_session_vec_table`). The text
embedded is the same title + message-body concatenation that feeds the FTS
``search_index`` row, so keyword and semantic search see the same content.

Everything here is **best-effort**: when sqlite-vec or fastembed is missing —
or an individual embed fails — the affected sessions simply get no vector and
search falls back to FTS. A vector failure must never break the index write,
so this runs in its own transaction *after* the main ``write_sessions`` commit,
never inside it (embedding is slow and would hold the write lock).
"""

from __future__ import annotations

import logging
import sqlite3
from typing import Iterable, Tuple

from .embeddings import DEFAULT_MODEL, embed_text, embeddings_available, pack_vector
from .schema import ensure_session_vec_table

logger = logging.getLogger(__name__)

# fastembed's bge-small truncates well before this, but cap the input so a
# pathological multi-megabyte session doesn't spend seconds tokenising text the
# model will discard anyway. Roughly a few thousand tokens of head context.
_MAX_EMBED_CHARS = 20_000

SessionText = Tuple[str, str]  # (session_id, text to embed)


def embed_sessions(conn: sqlite3.Connection, items: Iterable[SessionText]) -> int:
    """Embed each ``(session_id, text)`` into ``session_embeddings``.

    Returns the number of vectors written. Returns 0 (without raising) when the
    vector table or the embedding backend is unavailable — the caller keeps its
    FTS-only index. Uses ``INSERT OR REPLACE`` keyed on ``session_id`` so a
    re-index refreshes vectors in place.
    """
    items = list(items)
    if not items:
        return 0
    if not embeddings_available() or not ensure_session_vec_table(conn):
        return 0

    written = 0
    try:
        conn.execute("BEGIN")
        # Full replace mirrors write_sessions' rebuild semantics: stale rows for
        # sessions that vanished upstream must not linger in the vector table.
        conn.execute("DELETE FROM session_embeddings")
        for session_id, text in items:
            vector = embed_text((text or "")[:_MAX_EMBED_CHARS])
            if vector is None:
                continue  # empty text or a transient embed failure — skip, FTS covers it
            conn.execute(
                "INSERT OR REPLACE INTO session_embeddings(session_id, model, embedding) "
                "VALUES (?, ?, ?)",
                (session_id, DEFAULT_MODEL, pack_vector(vector)),
            )
            written += 1
        conn.execute("COMMIT")
    except sqlite3.Error as exc:
        logger.warning("Session embedding pass failed, leaving FTS-only: %s", exc)
        try:
            conn.execute("ROLLBACK")
        except sqlite3.OperationalError:
            pass
        return 0
    return written
