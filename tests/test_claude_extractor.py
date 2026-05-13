"""Tests for ai_history/extractors/claude.py."""

from __future__ import annotations

import json
from pathlib import Path

from ai_history.core.models import Role, Tool
from ai_history.extractors.claude import ClaudeCodeExtractor


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")


def _ts(t: str = "2025-06-15T10:00:00") -> str:
    return t


def _minimal_records(session_id: str = "sess-abc123") -> list[dict]:
    return [
        {
            "type": "user",
            "timestamp": _ts("2025-06-15T10:00:00"),
            "sessionId": session_id,
            "message": {"role": "user", "content": "Please implement quicksort"},
            "uuid": "uuid-001",
            "version": "1.5.0",
            "gitBranch": "main",
        },
        {
            "type": "assistant",
            "timestamp": _ts("2025-06-15T10:01:00"),
            "sessionId": session_id,
            "message": {"role": "assistant", "content": "Here is quicksort implementation."},
            "uuid": "uuid-002",
        },
    ]


def _make_project_dir(tmp_path: Path, project_dir_name: str = "-home-user-projects-app") -> tuple[Path, Path]:
    """Create .claude/projects/<project_dir>/ and return (projects_dir, project_dir)."""
    projects = tmp_path / ".claude" / "projects"
    project = projects / project_dir_name
    project.mkdir(parents=True)
    return projects, project


# ---------------------------------------------------------------------------
# Availability
# ---------------------------------------------------------------------------


def test_claude_not_available_when_no_dirs(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    extractor = ClaudeCodeExtractor()
    assert extractor.is_available() is False


def test_claude_available_when_projects_exist(monkeypatch, tmp_path):
    projects = tmp_path / ".claude" / "projects"
    projects.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(tmp_path))
    extractor = ClaudeCodeExtractor()
    assert extractor.is_available() is True


def test_claude_tool_property(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    extractor = ClaudeCodeExtractor()
    assert extractor.tool == Tool.CLAUDE_CODE


def test_claude_extract_empty_when_unavailable(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    extractor = ClaudeCodeExtractor()
    assert list(extractor.extract_sessions()) == []


# ---------------------------------------------------------------------------
# Parsing JSONL sessions
# ---------------------------------------------------------------------------


def test_parse_basic_session(monkeypatch, tmp_path):
    _, project = _make_project_dir(tmp_path)
    jsonl = project / "sess-abc123.jsonl"
    _write_jsonl(jsonl, _minimal_records("sess-abc123"))
    monkeypatch.setenv("HOME", str(tmp_path))

    extractor = ClaudeCodeExtractor()
    sessions = list(extractor.extract_sessions())
    assert len(sessions) == 1
    s = sessions[0]
    assert s.session_id == "sess-abc123"
    assert s.tool == Tool.CLAUDE_CODE
    assert s.git_branch == "main"
    assert s.cli_version == "1.5.0"


def test_parse_session_message_roles(monkeypatch, tmp_path):
    _, project = _make_project_dir(tmp_path)
    jsonl = project / "sess-roles.jsonl"
    _write_jsonl(jsonl, _minimal_records("sess-roles"))
    monkeypatch.setenv("HOME", str(tmp_path))

    extractor = ClaudeCodeExtractor()
    sessions = list(extractor.extract_sessions())
    msgs = sessions[0].messages
    assert msgs[0].role == Role.USER
    assert msgs[1].role == Role.ASSISTANT


def test_parse_session_with_summary(monkeypatch, tmp_path):
    _, project = _make_project_dir(tmp_path)
    records = _minimal_records("sess-summary")
    records.insert(0, {
        "type": "summary",
        "timestamp": _ts(),
        "summary": "Session about implementing sorting algorithms",
    })
    jsonl = project / "sess-summary.jsonl"
    _write_jsonl(jsonl, records)
    monkeypatch.setenv("HOME", str(tmp_path))

    extractor = ClaudeCodeExtractor()
    sessions = list(extractor.extract_sessions())
    s = sessions[0]
    assert s.title == "Session about implementing sorting algorithms"
    assert s.summary == "Session about implementing sorting algorithms"


def test_parse_session_bad_summary_filtered(monkeypatch, tmp_path):
    """Bad summary is filtered; title falls back to first user message via _normalize_session."""
    _, project = _make_project_dir(tmp_path)
    records = _minimal_records("sess-badsummary")
    records.insert(0, {
        "type": "summary",
        "timestamp": _ts(),
        "summary": "agents.md instructions for this session",
    })
    jsonl = project / "sess-badsummary.jsonl"
    _write_jsonl(jsonl, records)
    monkeypatch.setenv("HOME", str(tmp_path))

    extractor = ClaudeCodeExtractor()
    sessions = list(extractor.extract_sessions())
    s = sessions[0]
    # summary is None, title may be derived from first user message by _normalize_session
    assert s.summary is None


def test_parse_session_summary_with_bad_markers(monkeypatch, tmp_path):
    """Summaries containing bad markers are sanitized to None."""
    _, project = _make_project_dir(tmp_path)
    records = _minimal_records("sess-markers")
    # Add a bad summary record
    records.insert(0, {
        "type": "summary",
        "timestamp": _ts(),
        "summary": "<command-name>some name</command-name>",
    })
    jsonl = project / "sess-markers.jsonl"
    _write_jsonl(jsonl, records)
    monkeypatch.setenv("HOME", str(tmp_path))

    extractor = ClaudeCodeExtractor()
    sessions = list(extractor.extract_sessions())
    # summary should be None (sanitized), title may be set from first user message
    assert sessions[0].summary is None


def test_parse_session_non_string_summary(monkeypatch, tmp_path):
    """Non-string summary values are sanitized to None."""
    _, project = _make_project_dir(tmp_path)
    records = _minimal_records("sess-nonstr")
    records.insert(0, {"type": "summary", "timestamp": _ts(), "summary": 12345})
    jsonl = project / "sess-nonstr.jsonl"
    _write_jsonl(jsonl, records)
    monkeypatch.setenv("HOME", str(tmp_path))

    extractor = ClaudeCodeExtractor()
    sessions = list(extractor.extract_sessions())
    assert sessions[0].summary is None


def test_parse_content_list_text_items(monkeypatch, tmp_path):
    _, project = _make_project_dir(tmp_path)
    records = [
        {
            "type": "user",
            "timestamp": _ts(),
            "sessionId": "sess-textlist",
            "message": {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Part one"},
                    {"type": "text", "text": "Part two"},
                ],
            },
            "uuid": "u-001",
        },
        {
            "type": "assistant",
            "timestamp": _ts("2025-06-15T10:01:00"),
            "sessionId": "sess-textlist",
            "message": {"role": "assistant", "content": "Reply here"},
            "uuid": "a-001",
        },
    ]
    jsonl = project / "sess-textlist.jsonl"
    _write_jsonl(jsonl, records)
    monkeypatch.setenv("HOME", str(tmp_path))

    extractor = ClaudeCodeExtractor()
    sessions = list(extractor.extract_sessions())
    user_msgs = [m for m in sessions[0].messages if m.role == Role.USER]
    assert "Part one" in user_msgs[0].content
    assert "Part two" in user_msgs[0].content


def test_parse_content_list_tool_use_bash(monkeypatch, tmp_path):
    _, project = _make_project_dir(tmp_path)
    records = [
        {
            "type": "user",
            "timestamp": _ts(),
            "sessionId": "sess-tool-bash",
            "message": {"role": "user", "content": "Run ls"},
            "uuid": "u-001",
        },
        {
            "type": "assistant",
            "timestamp": _ts("2025-06-15T10:01:00"),
            "sessionId": "sess-tool-bash",
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Bash",
                        "input": {"command": "ls -la /tmp"},
                    }
                ],
            },
            "uuid": "a-001",
        },
    ]
    jsonl = project / "sess-tool-bash.jsonl"
    _write_jsonl(jsonl, records)
    monkeypatch.setenv("HOME", str(tmp_path))

    extractor = ClaudeCodeExtractor()
    sessions = list(extractor.extract_sessions())
    assistant_msgs = [m for m in sessions[0].messages if m.role == Role.ASSISTANT]
    assert any("ls -la /tmp" in m.content for m in assistant_msgs)


def test_parse_content_list_tool_use_read_write_edit(monkeypatch, tmp_path):
    _, project = _make_project_dir(tmp_path)
    records = [
        {
            "type": "user",
            "timestamp": _ts(),
            "sessionId": "sess-rwe",
            "message": {"role": "user", "content": "Read, write and edit files"},
            "uuid": "u-001",
        },
        {
            "type": "assistant",
            "timestamp": _ts("2025-06-15T10:01:00"),
            "sessionId": "sess-rwe",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "tool_use", "name": "Read", "input": {"file_path": "/foo/a.py"}},
                    {"type": "tool_use", "name": "Write", "input": {"file_path": "/foo/b.py"}},
                    {"type": "tool_use", "name": "Edit", "input": {"file_path": "/foo/c.py"}},
                ],
            },
            "uuid": "a-001",
        },
    ]
    jsonl = project / "sess-rwe.jsonl"
    _write_jsonl(jsonl, records)
    monkeypatch.setenv("HOME", str(tmp_path))

    extractor = ClaudeCodeExtractor()
    sessions = list(extractor.extract_sessions())
    assistant_msgs = [m for m in sessions[0].messages if m.role == Role.ASSISTANT]
    combined = " ".join(m.content for m in assistant_msgs)
    assert "a.py" in combined
    assert "b.py" in combined
    assert "c.py" in combined


def test_parse_content_list_glob_grep(monkeypatch, tmp_path):
    _, project = _make_project_dir(tmp_path)
    records = [
        {
            "type": "user",
            "timestamp": _ts(),
            "sessionId": "sess-glob-grep",
            "message": {"role": "user", "content": "Find patterns"},
            "uuid": "u-001",
        },
        {
            "type": "assistant",
            "timestamp": _ts("2025-06-15T10:01:00"),
            "sessionId": "sess-glob-grep",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "tool_use", "name": "Glob", "input": {"pattern": "**/*.py"}},
                    {"type": "tool_use", "name": "Grep", "input": {"pattern": "import pytest"}},
                ],
            },
            "uuid": "a-001",
        },
    ]
    jsonl = project / "sess-glob-grep.jsonl"
    _write_jsonl(jsonl, records)
    monkeypatch.setenv("HOME", str(tmp_path))

    extractor = ClaudeCodeExtractor()
    sessions = list(extractor.extract_sessions())
    combined = " ".join(m.content for m in sessions[0].messages)
    assert "**/*.py" in combined
    assert "import pytest" in combined


def test_parse_content_list_generic_tool(monkeypatch, tmp_path):
    _, project = _make_project_dir(tmp_path)
    records = [
        {
            "type": "user",
            "timestamp": _ts(),
            "sessionId": "sess-generic-tool",
            "message": {"role": "user", "content": "Use custom tool"},
            "uuid": "u-001",
        },
        {
            "type": "assistant",
            "timestamp": _ts("2025-06-15T10:01:00"),
            "sessionId": "sess-generic-tool",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "tool_use", "name": "MyCustomTool", "input": {"key": "value"}},
                ],
            },
            "uuid": "a-001",
        },
    ]
    jsonl = project / "sess-generic-tool.jsonl"
    _write_jsonl(jsonl, records)
    monkeypatch.setenv("HOME", str(tmp_path))

    extractor = ClaudeCodeExtractor()
    sessions = list(extractor.extract_sessions())
    combined = " ".join(m.content for m in sessions[0].messages)
    assert "MyCustomTool" in combined


def test_parse_content_list_tool_result(monkeypatch, tmp_path):
    _, project = _make_project_dir(tmp_path)
    records = [
        {
            "type": "user",
            "timestamp": _ts(),
            "sessionId": "sess-tool-result",
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "tool-abc",
                        "content": "The result of the tool call",
                    }
                ],
            },
            "uuid": "u-001",
        },
        {
            "type": "assistant",
            "timestamp": _ts("2025-06-15T10:01:00"),
            "sessionId": "sess-tool-result",
            "message": {"role": "assistant", "content": "Processed the result"},
            "uuid": "a-001",
        },
    ]
    jsonl = project / "sess-tool-result.jsonl"
    _write_jsonl(jsonl, records)
    monkeypatch.setenv("HOME", str(tmp_path))

    extractor = ClaudeCodeExtractor()
    sessions = list(extractor.extract_sessions())
    user_msgs = [m for m in sessions[0].messages if m.role == Role.USER]
    assert any("[Tool Result]" in m.content for m in user_msgs)


def test_parse_content_list_long_tool_result_truncated(monkeypatch, tmp_path):
    _, project = _make_project_dir(tmp_path)
    long_content = "x" * 600  # > 500 chars
    records = [
        {
            "type": "user",
            "timestamp": _ts(),
            "sessionId": "sess-long-result",
            "message": {
                "role": "user",
                "content": [
                    {"type": "tool_result", "tool_use_id": "t1", "content": long_content},
                ],
            },
            "uuid": "u-001",
        },
        {
            "type": "assistant",
            "timestamp": _ts("2025-06-15T10:01:00"),
            "sessionId": "sess-long-result",
            "message": {"role": "assistant", "content": "Done"},
            "uuid": "a-001",
        },
    ]
    jsonl = project / "sess-long-result.jsonl"
    _write_jsonl(jsonl, records)
    monkeypatch.setenv("HOME", str(tmp_path))

    extractor = ClaudeCodeExtractor()
    sessions = list(extractor.extract_sessions())
    user_msgs = [m for m in sessions[0].messages if m.role == Role.USER]
    combined = " ".join(m.content for m in user_msgs)
    assert "..." in combined


def test_parse_content_list_string_items(monkeypatch, tmp_path):
    """String items in content list are appended directly."""
    _, project = _make_project_dir(tmp_path)
    records = [
        {
            "type": "user",
            "timestamp": _ts(),
            "sessionId": "sess-str-items",
            "message": {
                "role": "user",
                "content": ["Direct string part one", "Direct string part two"],
            },
            "uuid": "u-001",
        },
        {
            "type": "assistant",
            "timestamp": _ts("2025-06-15T10:01:00"),
            "sessionId": "sess-str-items",
            "message": {"role": "assistant", "content": "Got it"},
            "uuid": "a-001",
        },
    ]
    jsonl = project / "sess-str-items.jsonl"
    _write_jsonl(jsonl, records)
    monkeypatch.setenv("HOME", str(tmp_path))

    extractor = ClaudeCodeExtractor()
    sessions = list(extractor.extract_sessions())
    user_msgs = [m for m in sessions[0].messages if m.role == Role.USER]
    assert any("Direct string part one" in m.content for m in user_msgs)


def test_parse_invalid_json_lines_skipped(monkeypatch, tmp_path):
    _, project = _make_project_dir(tmp_path)
    jsonl = project / "sess-corrupt.jsonl"
    jsonl.write_text(
        json.dumps({
            "type": "user",
            "timestamp": "2025-06-15T10:00:00",
            "sessionId": "sess-corrupt",
            "message": {"role": "user", "content": "Valid message"},
            "uuid": "u-001",
        }) + "\n"
        "NOT VALID JSON\n"
        + json.dumps({
            "type": "assistant",
            "timestamp": "2025-06-15T10:01:00",
            "sessionId": "sess-corrupt",
            "message": {"role": "assistant", "content": "Valid reply"},
            "uuid": "a-001",
        }) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("HOME", str(tmp_path))

    extractor = ClaudeCodeExtractor()
    sessions = list(extractor.extract_sessions())
    assert len(sessions) == 1
    assert sessions[0].message_count == 2


def test_parse_fallback_timestamps_from_mtime(monkeypatch, tmp_path):
    """Sessions with no timestamps use file mtime."""
    _, project = _make_project_dir(tmp_path)
    jsonl = project / "sess-notime.jsonl"
    # Records without timestamp
    records = [
        {"type": "user", "sessionId": "sess-notime", "message": {"role": "user", "content": "Hello"}, "uuid": "u1"},
        {"type": "assistant", "sessionId": "sess-notime", "message": {"role": "assistant", "content": "Hi"}, "uuid": "a1"},
    ]
    _write_jsonl(jsonl, records)
    monkeypatch.setenv("HOME", str(tmp_path))

    extractor = ClaudeCodeExtractor()
    sessions = list(extractor.extract_sessions())
    s = sessions[0]
    assert s.created_at is not None
    assert s.last_updated is not None


# ---------------------------------------------------------------------------
# _decode_project_name
# ---------------------------------------------------------------------------


def test_decode_project_name_no_leading_dash():
    extractor = ClaudeCodeExtractor.__new__(ClaudeCodeExtractor)
    result = extractor._decode_project_name("myproject")
    assert result == "myproject"


def test_decode_project_name_with_dash():
    extractor = ClaudeCodeExtractor.__new__(ClaudeCodeExtractor)
    # A path like /home/user/projects encoded as -home-user-projects
    result = extractor._decode_project_name("-home-user-projects")
    # Result varies depending on which dirs exist on filesystem
    assert result.startswith("/")


# ---------------------------------------------------------------------------
# _sanitize_summary
# ---------------------------------------------------------------------------


def test_sanitize_summary_empty_string():
    extractor = ClaudeCodeExtractor.__new__(ClaudeCodeExtractor)
    assert extractor._sanitize_summary("") is None


def test_sanitize_summary_whitespace_only():
    extractor = ClaudeCodeExtractor.__new__(ClaudeCodeExtractor)
    assert extractor._sanitize_summary("   ") is None


def test_sanitize_summary_non_string():
    extractor = ClaudeCodeExtractor.__new__(ClaudeCodeExtractor)
    assert extractor._sanitize_summary(None) is None
    assert extractor._sanitize_summary(42) is None


def test_sanitize_summary_ok():
    extractor = ClaudeCodeExtractor.__new__(ClaudeCodeExtractor)
    result = extractor._sanitize_summary("Implement a binary search algorithm")
    assert result == "Implement a binary search algorithm"


def test_sanitize_summary_strips_whitespace():
    extractor = ClaudeCodeExtractor.__new__(ClaudeCodeExtractor)
    result = extractor._sanitize_summary("  Valid summary  ")
    assert result == "Valid summary"


def test_sanitize_summary_command_name_marker():
    extractor = ClaudeCodeExtractor.__new__(ClaudeCodeExtractor)
    assert extractor._sanitize_summary("Using <command-name> for this") is None


def test_sanitize_summary_command_message_marker():
    extractor = ClaudeCodeExtractor.__new__(ClaudeCodeExtractor)
    assert extractor._sanitize_summary("<command-message> was sent") is None


def test_sanitize_summary_command_args_marker():
    extractor = ClaudeCodeExtractor.__new__(ClaudeCodeExtractor)
    assert extractor._sanitize_summary("Args: <command-args>") is None
