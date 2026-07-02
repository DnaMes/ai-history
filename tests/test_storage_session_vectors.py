"""Tests for per-session vector population (#87, PR 2).

``embed_sessions`` writes one vector per session into the vec0
``session_embeddings`` table, and ``write_sessions`` calls it best-effort
after its FTS commit. Both degrade to a no-op (0 vectors, no crash) when
sqlite-vec or fastembed is unavailable.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from lore.core.models import Role, Tool, UnifiedMessage, UnifiedSession
from lore.storage import session_vectors, v2_db_path, write_sessions
from lore.storage.embeddings import embeddings_available, sqlite_vec_available
from lore.storage.schema import initialise
from lore.storage.session_vectors import embed_sessions

# Real vectors need BOTH the extension (to store/query) and the model (to embed).
requires_vectors = pytest.mark.skipif(
    not (sqlite_vec_available() and embeddings_available()),
    reason="needs the 'semantic' extra (sqlite-vec + fastembed)",
)


def _session(sid: str, title: str = "Sample", n_messages: int = 2) -> UnifiedSession:
    msgs = [
        UnifiedMessage(
            role=Role.USER if i % 2 == 0 else Role.ASSISTANT,
            content=f"message body {i} about {title}",
            timestamp=datetime(2026, 1, 1, 12, i),
        )
        for i in range(n_messages)
    ]
    return UnifiedSession(
        tool=Tool.CLAUDE_CODE,
        session_id=sid,
        created_at=datetime(2026, 1, 1),
        last_updated=datetime(2026, 1, 2),
        project_path="/home/u/proj",
        title=title,
        messages=msgs,
    )


def _vec_count(conn) -> int:
    return conn.execute("SELECT COUNT(*) FROM session_embeddings").fetchone()[0]


# ---------------------------------------------------------------------------
# embed_sessions — direct
# ---------------------------------------------------------------------------


@requires_vectors
def test_embed_sessions_writes_one_vector_each(tmp_path):
    conn = initialise(tmp_path / "index_v2.sqlite")
    written = embed_sessions(conn, [("a", "hello world"), ("b", "goodbye moon")])
    assert written == 2
    assert _vec_count(conn) == 2


@requires_vectors
def test_embed_sessions_skips_empty_text(tmp_path):
    conn = initialise(tmp_path / "index_v2.sqlite")
    written = embed_sessions(conn, [("a", "real text"), ("b", ""), ("c", "   ")])
    assert written == 1  # only 'a' had embeddable text
    assert _vec_count(conn) == 1


@requires_vectors
def test_embed_sessions_is_full_replace(tmp_path):
    conn = initialise(tmp_path / "index_v2.sqlite")
    embed_sessions(conn, [("old-1", "x"), ("old-2", "y")])
    embed_sessions(conn, [("new-1", "z")])
    rows = {r[0] for r in conn.execute("SELECT session_id FROM session_embeddings")}
    assert rows == {"new-1"}


def test_embed_sessions_empty_input_is_zero(tmp_path):
    conn = initialise(tmp_path / "index_v2.sqlite")
    assert embed_sessions(conn, []) == 0


@requires_vectors
def test_embed_sessions_deduplicates_ids(tmp_path):
    """Duplicate session ids must not kill the pass (regression).

    vec0 ignores INSERT OR REPLACE and raises 'UNIQUE constraint failed' on a
    duplicate key — real batches contain duplicate ids (same reason the
    sessions table uses INSERT OR REPLACE), which zeroed out the first real
    reindex. Last duplicate wins, matching the sessions-table semantics.
    """
    conn = initialise(tmp_path / "index_v2.sqlite")
    written = embed_sessions(conn, [("dup", "first text"), ("dup", "second text"), ("b", "other")])
    assert written == 2  # dup collapsed to one row, not a crashed pass
    assert _vec_count(conn) == 2


# ---------------------------------------------------------------------------
# Graceful degradation — no backend
# ---------------------------------------------------------------------------


def test_embed_sessions_noop_without_embeddings(tmp_path, monkeypatch):
    """No fastembed → 0 vectors, no crash."""
    monkeypatch.setattr(session_vectors, "embeddings_available", lambda: False)
    conn = initialise(tmp_path / "index_v2.sqlite")
    assert embed_sessions(conn, [("a", "text")]) == 0


def test_embed_sessions_noop_without_vec_table(tmp_path, monkeypatch):
    """No vec0 table → 0 vectors, no crash."""
    monkeypatch.setattr(session_vectors, "embeddings_available", lambda: True)
    monkeypatch.setattr(session_vectors, "ensure_session_vec_table", lambda conn: False)
    conn = initialise(tmp_path / "index_v2.sqlite")
    assert embed_sessions(conn, [("a", "text")]) == 0


# ---------------------------------------------------------------------------
# write_sessions integration — vectors populated after FTS commit
# ---------------------------------------------------------------------------


@requires_vectors
def test_write_sessions_populates_vectors(tmp_path):
    db = v2_db_path(tmp_path)
    count = write_sessions(db, [_session("a"), _session("b", title="Other")])
    assert count == 2
    conn = initialise(db)
    assert _vec_count(conn) == 2


@requires_vectors
def test_write_sessions_vectors_track_full_replace(tmp_path):
    db = v2_db_path(tmp_path)
    write_sessions(db, [_session("old")])
    write_sessions(db, [_session("new")])
    conn = initialise(db)
    rows = {r[0] for r in conn.execute("SELECT session_id FROM session_embeddings")}
    assert rows == {"new"}


def test_write_sessions_succeeds_without_backend(tmp_path, monkeypatch):
    """The index write completes and FTS is intact even with no vector backend."""
    monkeypatch.setattr("lore.storage.writer.embed_sessions", lambda conn, items: 0)
    db = v2_db_path(tmp_path)
    count = write_sessions(db, [_session("a", title="Findable")])
    assert count == 1
    conn = initialise(db)
    # FTS row still written regardless of vectors.
    hits = conn.execute(
        "SELECT entity_id FROM search_index WHERE search_index MATCH 'Findable'"
    ).fetchall()
    assert any(r[0] == "a" for r in hits)


def test_write_sessions_survives_embed_exception(tmp_path, monkeypatch):
    """An embedding crash must not roll back the committed index."""

    def boom(conn, items):
        raise RuntimeError("embed exploded")

    monkeypatch.setattr("lore.storage.writer.embed_sessions", boom)
    db = v2_db_path(tmp_path)
    count = write_sessions(db, [_session("a")])
    assert count == 1  # index still committed
    conn = initialise(db)
    assert conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 1
