import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Iterator

from ..core.models import Role, Tool, UnifiedMessage, UnifiedSession
from ..utils.datetime import parse_timestamp
from ..utils.home_discovery import discover_home_marker_paths
from ..utils.paths import make_thread_id
from .base import BaseExtractor

logger = logging.getLogger(__name__)


class ClaudeCodeExtractor(BaseExtractor):
    """Extract chat history from Claude Code."""

    def __init__(self):
        self.base_path = Path.home() / ".claude" / "projects"
        self.base_paths = self._discover_base_paths()

    def _discover_base_paths(self):
        paths = [self.base_path]
        for candidate in discover_home_marker_paths(".claude/projects"):
            if candidate not in paths:
                paths.append(candidate)
        return [path for path in paths if path.exists()]

    @property
    def tool(self) -> Tool:
        return Tool.CLAUDE_CODE

    def is_available(self) -> bool:
        return len(self.base_paths) > 0

    def _decode_project_name(self, encoded: str) -> str:
        """Decode project path from directory name."""
        if not encoded.startswith("-"):
            return encoded

        # Remove leading dash and split by dash
        parts = encoded[1:].split("-")

        # Try to reconstruct the path by testing which combinations exist
        result_parts = []
        current = ""

        for i, part in enumerate(parts):
            if current:
                test_path = current + "-" + part
            else:
                test_path = part

            if result_parts:
                full_test = "/" + "/".join(result_parts) + "/" + test_path
            else:
                full_test = "/" + test_path

            if os.path.exists(full_test):
                result_parts.append(test_path)
                current = ""
            else:
                current = test_path

        if current:
            result_parts.append(current)

        if result_parts:
            return "/" + "/".join(result_parts)

        return "/" + encoded[1:].replace("-", "/")

    def extract_sessions(self) -> Iterator[UnifiedSession]:
        if not self.is_available():
            return

        for base_path in self.base_paths:
            for project_dir in base_path.iterdir():
                if not project_dir.is_dir():
                    continue

                project_path = self._decode_project_name(project_dir.name)

                for jsonl_file in project_dir.glob("*.jsonl"):
                    try:
                        session = self._parse_session(jsonl_file, project_path)

                        if self.should_import_session(session):
                            yield session
                    except Exception as e:
                        logger.warning("Failed to parse %s: %s", jsonl_file, e)

    def _parse_session(self, path: Path, project_path: str) -> UnifiedSession:
        """Parse a single JSONL session file."""
        messages = []
        summary = None
        session_id = path.stem
        cli_version = None
        git_branch = None
        created_at = None
        last_updated = None

        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue

                record_type = record.get("type")

                if record_type == "summary":
                    summary = self._sanitize_summary(record.get("summary"))
                elif record_type in ("user", "assistant"):
                    msg_data = record.get("message", {})
                    role = Role.USER if record_type == "user" else Role.ASSISTANT
                    content = msg_data.get("content", "")

                    # Handle content that is a list (tool use, etc.)
                    if isinstance(content, list):
                        text_parts = []
                        tool_calls = []
                        for item in content:
                            if isinstance(item, dict):
                                if item.get("type") == "text":
                                    text_parts.append(item.get("text", ""))
                                elif item.get("type") == "tool_use":
                                    tool_calls.append(item)
                                    tool_name = item.get("name", "Unknown")
                                    tool_input = item.get("input", {})
                                    if isinstance(tool_input, dict):
                                        if tool_name == "Bash":
                                            cmd = tool_input.get("command", "")
                                            text_parts.append(
                                                f"[Tool: {tool_name}]\n```bash\n{cmd}\n```"
                                            )
                                        elif tool_name in ("Read", "Write", "Edit"):
                                            file_path = tool_input.get("file_path", "")
                                            text_parts.append(f"[Tool: {tool_name}] {file_path}")
                                        elif tool_name == "Glob":
                                            pattern = tool_input.get("pattern", "")
                                            text_parts.append(f"[Tool: {tool_name}] {pattern}")
                                        elif tool_name == "Grep":
                                            pattern = tool_input.get("pattern", "")
                                            text_parts.append(f"[Tool: {tool_name}] {pattern}")
                                        else:
                                            text_parts.append(f"[Tool: {tool_name}]")
                                elif item.get("type") == "tool_result":
                                    tool_id = item.get("tool_use_id", "")
                                    result_content = item.get("content", "")
                                    if (
                                        isinstance(result_content, str)
                                        and len(result_content) > 500
                                    ):
                                        result_content = result_content[:500] + "..."
                                    text_parts.append(f"[Tool Result]\n{result_content}")
                            elif isinstance(item, str):
                                text_parts.append(item)
                        content = "\n".join(text_parts)
                    else:
                        tool_calls = []

                    timestamp = parse_timestamp(record.get("timestamp", ""))

                    if created_at is None or timestamp < created_at:
                        created_at = timestamp
                    if last_updated is None or timestamp > last_updated:
                        last_updated = timestamp

                    # Extract version and branch
                    if cli_version is None:
                        cli_version = record.get("version")
                    if git_branch is None:
                        git_branch = record.get("gitBranch")
                    if session_id == path.stem:
                        session_id = record.get("sessionId", path.stem)

                    messages.append(
                        UnifiedMessage(
                            role=role,
                            content=content,
                            timestamp=timestamp,
                            message_id=record.get("uuid"),
                            tool_calls=tool_calls if tool_calls else [],
                        )
                    )

        if created_at is None:
            created_at = datetime.fromtimestamp(path.stat().st_mtime)
        if last_updated is None:
            last_updated = datetime.fromtimestamp(path.stat().st_mtime)

        return UnifiedSession(
            tool=Tool.CLAUDE_CODE,
            session_id=session_id,
            created_at=created_at,
            last_updated=last_updated,
            messages=messages,
            project_path=project_path,
            thread_id=make_thread_id(project_path=project_path),
            title=summary,
            summary=summary,
            cli_version=cli_version,
            git_branch=git_branch,
            source_path=str(path),
        )

    def _sanitize_summary(self, value):
        if not isinstance(value, str):
            return None
        summary = value.strip()
        if not summary:
            return None

        lowered = summary.lower()
        bad_markers = (
            "<command-name>",
            "<command-message>",
            "<command-args>",
            "agents.md instructions",
            "instructions for /home",
        )
        if any(marker in lowered for marker in bad_markers):
            return None

        return summary
