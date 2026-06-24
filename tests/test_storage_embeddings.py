"""Tests for the optional semantic-memory layer (#33).

The embedding backend (fastembed) is optional. These tests split into:
- pure-function tests (pack/unpack/cosine) that always run;
- embedding-dependent tests, skipped when the backend is unavailable so
  CI without the 'semantic' extra still passes.
"""

from __future__ import annotations

import pytest

from lore.storage import add_memory, recall_memory
from lore.storage.embeddings import (
    cosine_similarity,
    embeddings_available,
    pack_vector,
    unpack_vector,
)

requires_embeddings = pytest.mark.skipif(
    not embeddings_available(),
    reason="optional 'semantic' extra (fastembed) not installed",
)


# ---------------------------------------------------------------------------
# Pure vector helpers — always run
# ---------------------------------------------------------------------------


def test_pack_unpack_roundtrip():
    vec = [0.1, -0.25, 0.99, 0.0, -1.0]
    restored = unpack_vector(pack_vector(vec))
    assert len(restored) == len(vec)
    assert all(abs(a - b) < 1e-6 for a, b in zip(vec, restored))


def test_cosine_identical_vectors():
    assert abs(cosine_similarity([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) - 1.0) < 1e-6


def test_cosine_orthogonal_vectors():
    assert abs(cosine_similarity([1.0, 0.0], [0.0, 1.0])) < 1e-6


def test_cosine_zero_vector_is_safe():
    assert cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0


def test_cosine_length_mismatch_is_safe():
    assert cosine_similarity([1.0, 2.0], [1.0]) == 0.0


# ---------------------------------------------------------------------------
# Graceful degradation — semantic recall must work without the backend
# ---------------------------------------------------------------------------


def test_recall_semantic_falls_back_without_backend(tmp_path, monkeypatch):
    """With embeddings forced unavailable, semantic recall falls back to FTS."""
    import lore.storage.embeddings as emb

    monkeypatch.setattr(emb, "embed_text", lambda _text: None)

    add_memory(tmp_path, "fact", "Kubernetes scaling notes", "HPA autoscales pods")
    # semantic=True must still return the keyword match via FTS fallback.
    hits = recall_memory(tmp_path, "kubernetes", semantic=True)
    assert [h.title for h in hits] == ["Kubernetes scaling notes"]


def test_add_memory_works_without_embeddings(tmp_path, monkeypatch):
    """A missing embedding backend must not block writing memory."""
    import lore.storage.memory as mem

    # Force the embedding store helper to behave as if the backend is absent.
    monkeypatch.setattr(mem, "_store_embedding", lambda *a, **k: None)
    mid = add_memory(tmp_path, "note", "Plain memory", "no embedding here")
    assert mid > 0


# ---------------------------------------------------------------------------
# Real semantic ranking — only with the backend installed
# ---------------------------------------------------------------------------


@requires_embeddings
def test_semantic_recall_ranks_by_meaning(tmp_path):
    """The core of #33: a query finds thematically related memory even when
    no query word appears literally in it."""
    add_memory(
        tmp_path,
        "decision",
        "Postgres 16 for the stack",
        "We standardise on PostgreSQL 16 in Docker.",
    )
    add_memory(tmp_path, "fact", "Cats sleep a lot", "House cats sleep 12-16 hours a day.")
    add_memory(
        tmp_path, "lesson", "Connection pooling", "Database connection pooling cuts query latency."
    )

    hits = recall_memory(tmp_path, "database performance", semantic=True, limit=3)
    titles = [h.title for h in hits]
    # The two DB-related memories must rank above the unrelated cat fact.
    assert titles.index("Cats sleep a lot") == len(titles) - 1


@requires_embeddings
def test_embedding_stored_on_add(tmp_path):
    import sqlite3

    from lore.storage import v2_db_path

    mid = add_memory(tmp_path, "fact", "Embedded memory", "this gets a vector")
    conn = sqlite3.connect(v2_db_path(tmp_path))
    row = conn.execute("SELECT dim FROM memory_embeddings WHERE memory_id = ?", (mid,)).fetchone()
    assert row is not None
    assert row[0] > 0  # non-empty embedding dimension
