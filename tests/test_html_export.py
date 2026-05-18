"""Tests for the standalone single-file HTML session exporter (issue #28)."""

from __future__ import annotations

from datetime import datetime

from ai_history.core.models import Role, Tool, UnifiedMessage, UnifiedSession
from ai_history.exporters.html import render_session_html


def _make_session() -> UnifiedSession:
    ts = datetime(2026, 5, 18, 10, 30, 0)
    messages = [
        UnifiedMessage(
            role=Role.USER,
            content="How do I print in Python?",
            timestamp=ts,
        ),
        UnifiedMessage(
            role=Role.ASSISTANT,
            content="Use the print function:\n\n```python\nprint('hello')\n```",
            timestamp=ts,
        ),
        UnifiedMessage(
            role=Role.TOOL,
            content="ran command",
            timestamp=ts,
            tool_calls=[{"name": "Bash", "input": {"cmd": "ls"}}],
        ),
    ]
    return UnifiedSession(
        tool=Tool.CLAUDE_CODE,
        session_id="test-session-abc123",
        created_at=ts,
        last_updated=ts,
        messages=messages,
        project_path="/home/user/project",
        title="Python printing help",
    )


def test_contains_message_content() -> None:
    html_doc = render_session_html(_make_session())
    assert "How do I print in Python?" in html_doc
    assert "Use the print function" in html_doc
    assert "Python printing help" in html_doc


def test_is_self_contained() -> None:
    html_doc = render_session_html(_make_session())
    assert "<style>" in html_doc
    assert "<link rel=stylesheet" not in html_doc
    assert '<link rel="stylesheet"' not in html_doc
    assert 'src="http' not in html_doc
    assert 'href="http' not in html_doc
    assert "cdn" not in html_doc.lower()


def test_code_block_rendered_as_pre() -> None:
    html_doc = render_session_html(_make_session())
    assert "<pre><code>" in html_doc
    assert "print(&#x27;hello&#x27;)" in html_doc


def test_tool_call_rendered() -> None:
    html_doc = render_session_html(_make_session())
    assert "Tool: Bash" in html_doc
    assert "&quot;cmd&quot;" in html_doc


def test_html_in_content_is_escaped() -> None:
    ts = datetime(2026, 5, 18, 10, 30, 0)
    session = UnifiedSession(
        tool=Tool.CLAUDE_CODE,
        session_id="xss-test",
        created_at=ts,
        last_updated=ts,
        messages=[
            UnifiedMessage(
                role=Role.USER,
                content="<script>alert('xss')</script>",
                timestamp=ts,
            )
        ],
        title="<img src=x onerror=alert(1)>",
    )
    html_doc = render_session_html(session)
    assert "<script>alert" not in html_doc
    assert "&lt;script&gt;" in html_doc
    assert "<img src=x onerror" not in html_doc
    assert "&lt;img src=x" in html_doc


def test_valid_html_document() -> None:
    html_doc = render_session_html(_make_session())
    assert html_doc.startswith("<!DOCTYPE html>")
    assert html_doc.rstrip().endswith("</html>")
    assert "<title>" in html_doc
    assert "test-session-abc123" in html_doc


def test_empty_session_renders() -> None:
    ts = datetime(2026, 5, 18, 10, 30, 0)
    session = UnifiedSession(
        tool=Tool.CODEX,
        session_id="empty",
        created_at=ts,
        last_updated=ts,
        messages=[],
    )
    html_doc = render_session_html(session)
    assert "<!DOCTYPE html>" in html_doc
    assert "Messages: 0" in html_doc
