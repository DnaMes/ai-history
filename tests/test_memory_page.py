"""Tests for the /memory web page (#33).

The page browses and searches the shared agent-memory store and lets a
memory be deleted.
"""

from __future__ import annotations

import pytest

from ai_history.interfaces import web, web_data
from ai_history.storage import add_memory


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """Test client with the v2 store + INDEX_PATH pointed at a temp dir."""
    monkeypatch.setattr(web, "INDEX_PATH", tmp_path / "index.json")
    monkeypatch.setattr(web_data, "INDEX_PATH", tmp_path / "index.json")
    monkeypatch.setattr(web_data, "OUTPUT_DIR", tmp_path)
    with web.app.test_client() as c:
        yield c, tmp_path


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def test_memory_page_renders_empty(client):
    c, _ = client
    resp = c.get("/memory")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "No memory entries" in body


def test_memory_page_lists_entries(client):
    c, tmp_path = client
    add_memory(tmp_path, "decision", "Use Postgres 16", "Standardise on PG16.")
    add_memory(tmp_path, "fact", "API rate limit", "100 requests per minute.")
    body = c.get("/memory").get_data(as_text=True)
    assert "Use Postgres 16" in body
    assert "API rate limit" in body
    assert "2 entries" in body


def test_memory_page_kind_filter(client):
    c, tmp_path = client
    add_memory(tmp_path, "decision", "A decision entry", "body")
    add_memory(tmp_path, "fact", "A fact entry", "body")
    body = c.get("/memory?kind=fact").get_data(as_text=True)
    assert "A fact entry" in body
    assert "A decision entry" not in body


def test_memory_page_keyword_search(client):
    c, tmp_path = client
    add_memory(tmp_path, "fact", "Kubernetes notes", "ingress configuration")
    add_memory(tmp_path, "fact", "Database notes", "connection pooling")
    body = c.get("/memory?q=kubernetes").get_data(as_text=True)
    assert "Kubernetes notes" in body
    assert "Database notes" not in body


def test_memory_page_rejects_invalid_kind(client):
    c, _ = client
    assert c.get("/memory?kind=bogus").status_code == 400


def test_memory_page_rejects_invalid_query(client):
    c, _ = client
    assert c.get("/memory?q=" + "x" * 600).status_code == 400


# ---------------------------------------------------------------------------
# Deletion
# ---------------------------------------------------------------------------


def test_memory_delete_removes_entry(client):
    c, tmp_path = client
    mid = add_memory(tmp_path, "note", "Throwaway memory", "delete me")
    resp = c.post(f"/memory/{mid}/delete", headers={"Origin": "http://localhost"})
    assert resp.status_code == 302
    # The entry no longer appears on the page.
    body = c.get("/memory").get_data(as_text=True)
    assert "Throwaway memory" not in body


def test_memory_delete_rejects_cross_origin(client):
    c, tmp_path = client
    mid = add_memory(tmp_path, "note", "Protected memory", "keep me")
    resp = c.post(f"/memory/{mid}/delete", headers={"Origin": "http://evil.example.com"})
    assert resp.status_code == 403
    # The entry survives the rejected cross-origin delete.
    assert "Protected memory" in c.get("/memory").get_data(as_text=True)
