"""Tests for v2 SQLite search (issue #34).

`search_sessions` queries the v2 store's unified FTS5 index — so search
results and the session list come from the same store and stay consistent.
"""

from __future__ import annotations

from datetime import datetime

from ai_history.core.models import Role, Tool, UnifiedMessage, UnifiedSession
from ai_history.exporters.index import IndexBuilder
from ai_history.storage import search_sessions


def _session(sid, tool=Tool.CLAUDE_CODE, title="T", project="/p", body="hello world"):
    return UnifiedSession(
        tool=tool,
        session_id=sid,
        created_at=datetime(2026, 1, 1),
        last_updated=datetime(2026, 1, 2),
        project_path=project,
        title=title,
        messages=[UnifiedMessage(role=Role.USER, content=body, timestamp=datetime(2026, 1, 1))],
    )


def test_search_empty_when_no_store(tmp_path):
    assert search_sessions(tmp_path, "anything") == []


def test_search_empty_query_returns_nothing(tmp_path):
    IndexBuilder(tmp_path).build_index([_session("a")], {})
    assert search_sessions(tmp_path, "") == []
    assert search_sessions(tmp_path, "   ") == []


def test_search_matches_title(tmp_path):
    # A natural-length title survives IndexBuilder's low-quality-title filter.
    IndexBuilder(tmp_path).build_index(
        [_session("a", title="Docker compose setup walkthrough")], {}
    )
    hits = search_sessions(tmp_path, "compose")
    assert [h["session"]["id"] for h in hits] == ["a"]


def test_search_matches_message_body(tmp_path):
    """v2 FTS covers message content, not just titles — the key win of #34."""
    IndexBuilder(tmp_path).build_index(
        [_session("a", title="Generic", body="how to configure kubernetes ingress")], {}
    )
    hits = search_sessions(tmp_path, "kubernetes")
    assert [h["session"]["id"] for h in hits] == ["a"]


def test_search_prefix_matching(tmp_path):
    # "kubern" should prefix-match "kubernetes" (FTS5 prefix query).
    IndexBuilder(tmp_path).build_index(
        [_session("a", body="configuring kubernetes ingress rules")], {}
    )
    hits = search_sessions(tmp_path, "kubern")
    assert [h["session"]["id"] for h in hits] == ["a"]


def test_search_result_shape(tmp_path):
    IndexBuilder(tmp_path).build_index([_session("a", body="findme distinctive token")], {})
    hits = search_sessions(tmp_path, "findme")
    assert len(hits) == 1
    assert "session" in hits[0] and "score" in hits[0]
    assert isinstance(hits[0]["score"], float)
    assert hits[0]["session"]["id"] == "a"


def test_search_tool_filter(tmp_path):
    IndexBuilder(tmp_path).build_index(
        [
            _session("a", tool=Tool.CLAUDE_CODE, body="shared search term here"),
            _session("b", tool=Tool.CODEX, body="shared search term here"),
        ],
        {},
    )
    hits = search_sessions(tmp_path, "shared", tool="codex")
    assert [h["session"]["id"] for h in hits] == ["b"]


def test_search_project_filter(tmp_path):
    IndexBuilder(tmp_path).build_index(
        [
            _session("a", body="topic discussion content", project="/home/u/alpha"),
            _session("b", body="topic discussion content", project="/home/u/beta"),
        ],
        {},
    )
    hits = search_sessions(tmp_path, "topic", project="alpha")
    assert [h["session"]["id"] for h in hits] == ["a"]


def test_search_respects_limit(tmp_path):
    sessions = [_session(f"s{i}", body="common recurring keyword") for i in range(10)]
    IndexBuilder(tmp_path).build_index(sessions, {})
    hits = search_sessions(tmp_path, "common", limit=3)
    assert len(hits) == 3


def test_search_no_match_returns_empty(tmp_path):
    IndexBuilder(tmp_path).build_index([_session("a", body="apples and oranges")], {})
    assert search_sessions(tmp_path, "zzzznonexistent") == []


# ---------------------------------------------------------------------------
# web_data.search_index — v2 vs legacy fallback
# ---------------------------------------------------------------------------


def test_web_search_index_uses_v2_when_enabled(tmp_path, monkeypatch):
    from ai_history.interfaces import web_data

    monkeypatch.setattr(web_data, "INDEX_PATH", tmp_path / "index.json")
    monkeypatch.setenv("AI_HISTORY_USE_V2", "1")
    web_data.clear_index_cache()

    IndexBuilder(tmp_path).build_index(
        [_session("v2hit", body="searchable content via v2 store")], {}
    )
    hits = web_data.search_index("searchable")
    assert [h["session"]["id"] for h in hits] == ["v2hit"]


def test_web_search_index_falls_back_to_legacy(tmp_path, monkeypatch):
    from ai_history.interfaces import web_data

    monkeypatch.setattr(web_data, "INDEX_PATH", tmp_path / "index.json")
    monkeypatch.setenv("AI_HISTORY_USE_V2", "0")
    web_data.clear_index_cache()

    IndexBuilder(tmp_path).build_index(
        [_session("legacyhit", body="searchable content via legacy engine")], {}
    )
    hits = web_data.search_index("searchable")
    assert [h["session"]["id"] for h in hits] == ["legacyhit"]
