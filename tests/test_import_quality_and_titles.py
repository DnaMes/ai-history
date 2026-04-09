from datetime import datetime
from pathlib import Path

from ai_history.core.models import Role, Tool, UnifiedMessage, UnifiedSession
from ai_history.exporters.index import IndexBuilder
from ai_history.extractors.base import BaseExtractor
from ai_history_cli import _is_low_value_index_entry


class _DummyExtractor(BaseExtractor):
    @property
    def tool(self) -> Tool:
        return Tool.CODEX

    def extract_sessions(self):
        return iter(())


def _session(messages, title=None):
    now = datetime(2026, 3, 4, 12, 0, 0)
    return UnifiedSession(
        tool=Tool.GEMINI_CLI,
        session_id="ses_test_abcdef12",
        created_at=now,
        last_updated=now,
        messages=messages,
        title=title,
    )


def test_extract_prompt_outline_skips_kryptic_command_markup():
    builder = IndexBuilder(Path("/tmp"))
    messages = [
        UnifiedMessage(
            role=Role.USER,
            content="<command-name>login</command-name> <command-message>login</command-message>",
            timestamp=datetime(2026, 3, 4, 12, 0, 0),
        ),
        UnifiedMessage(
            role=Role.USER,
            content="please fix docker compose startup crash",
            timestamp=datetime(2026, 3, 4, 12, 1, 0),
        ),
    ]

    outline = builder._extract_prompt_outline(_session(messages))

    assert outline == "please fix docker compose startup crash"


def test_infer_title_rejects_low_quality_native_title():
    builder = IndexBuilder(Path("/tmp"))
    session = _session([], title="<command-name>login</command-name>")

    title = builder._infer_title(session, "clean install on fedora 43")

    assert "clean install on fedora 43" in title
    assert title.endswith("abcdef12")


def test_should_import_session_allows_single_prompt_session_after_relaxation():
    extractor = _DummyExtractor()
    session = _session(
        [
            UnifiedMessage(
                role=Role.USER,
                content="one prompt only",
                timestamp=datetime(2026, 3, 4, 12, 0, 0),
            ),
            UnifiedMessage(
                role=Role.ASSISTANT,
                content="long answer " * 400,
                timestamp=datetime(2026, 3, 4, 12, 1, 0),
            ),
        ]
    )

    assert extractor.should_import_session(session) is True


def test_is_low_value_index_entry_flags_thin_sessions():
    assert _is_low_value_index_entry({"id": "x", "prompts": 1, "messages": 2}) is True
    assert (
        _is_low_value_index_entry(
            {
                "id": "x",
                "prompts": 2,
                "messages": 3,
                "prompt_outline": "ok",
                "search_text": "small",
            }
        )
        is True
    )
    assert (
        _is_low_value_index_entry(
            {
                "id": "x",
                "prompts": 3,
                "messages": 6,
                "prompt_outline": "real debugging session",
                "search_text": "x" * 800,
            }
        )
        is False
    )


def test_infer_title_drops_copilot_mode_preamble_titles():
    builder = IndexBuilder(Path("/tmp"))
    session = _session([], title="/home/dnames on-request workspace-write restricted")

    title = builder._infer_title(session, "")

    assert title.startswith("Gemini Cli 2026-03-04")


def test_infer_title_drops_login_successful_titles():
    builder = IndexBuilder(Path("/tmp"))
    session = _session([], title="Login successful")

    title = builder._infer_title(session, "")

    assert title.startswith("Gemini Cli 2026-03-04")


def test_infer_title_drops_agents_template_prompt_titles():
    builder = IndexBuilder(Path("/tmp"))
    session = _session(
        [], title="Generate a file named AGENTS.md that serves as a contributor guide"
    )

    title = builder._infer_title(session, "")

    assert title.startswith("Gemini Cli 2026-03-04")
