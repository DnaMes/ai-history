"""Tests for the session-view prep-layer (lore/interfaces/session_view_prep.py)."""

from __future__ import annotations

from lore.interfaces.session_view_prep import (
    has_structured_tool_calls,
    render_message_body,
    strip_tool_blocks,
)


class _Msg:
    def __init__(self, content="", tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []


def _fmt_content(s):
    return f"<PROSE>{s.strip()}</PROSE>"


def _fmt_tools(tool_calls):
    parts = []
    for tc in tool_calls:
        out = tc.get("output", "")
        parts.append(f"<TOOL name={tc.get('name')} out={out!r}>")
    return "".join(parts)


def test_strip_tool_blocks_removes_inlined_tool_noise():
    content = "Here is the plan.\n[Tool: Read] /x/auth.py\n[Tool Result]\nline1\nline2"
    assert strip_tool_blocks(content) == "Here is the plan."


def test_strip_tool_blocks_keeps_trailing_prose():
    content = "Reading the file.\n[Tool: Read] /x\n[Tool Result]\nout\n\nNow I'll fix it."
    stripped = strip_tool_blocks(content)
    assert "Reading the file." in stripped
    assert "Now I'll fix it." in stripped
    assert "[Tool" not in stripped


def test_strip_tool_blocks_empty():
    assert strip_tool_blocks("") == ""
    assert strip_tool_blocks(None) == ""


def test_has_structured_tool_calls():
    assert has_structured_tool_calls(_Msg(tool_calls=[{"name": "Read"}])) is True
    assert has_structured_tool_calls(_Msg(content="hi")) is False


def test_render_prefers_structured_tool_calls_with_output():
    """A message with structured tool_calls renders prose + paired tool cards.

    This is the Axis-1 payoff: the full result lives in tool_calls[i].output and
    is rendered from there, not re-parsed from the flattened string.
    """
    msg = _Msg(
        content="Let me read it.\n[Tool: Read] /x/auth.py\n[Tool Result]\nthe full file body",
        tool_calls=[
            {"name": "Read", "input": {"file_path": "/x/auth.py"}, "output": "the full file body"}
        ],
    )
    html = render_message_body(
        msg, format_message_content_fn=_fmt_content, format_tool_calls_fn=_fmt_tools
    )
    assert "<PROSE>Let me read it.</PROSE>" in html
    assert "name=Read" in html
    assert "out='the full file body'" in html
    # The inlined [Tool: …] noise is NOT shown in the prose.
    assert "[Tool: Read]" not in html


def test_render_plain_content_when_no_tool_calls():
    msg = _Msg(content="just prose")
    html = render_message_body(
        msg, format_message_content_fn=_fmt_content, format_tool_calls_fn=_fmt_tools
    )
    assert html == "<PROSE>just prose</PROSE>"


def test_render_tool_calls_only_no_prose():
    msg = _Msg(content="", tool_calls=[{"name": "Bash", "output": "ok"}])
    html = render_message_body(
        msg, format_message_content_fn=_fmt_content, format_tool_calls_fn=_fmt_tools
    )
    assert html == "<TOOL name=Bash out='ok'>"


def test_render_empty_message():
    msg = _Msg(content="", tool_calls=[])
    html = render_message_body(
        msg, format_message_content_fn=_fmt_content, format_tool_calls_fn=_fmt_tools
    )
    assert html == ""
