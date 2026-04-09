#!/usr/bin/env python3
"""
DEPRECATED: This file is legacy and will be removed in a future version.

Please use the modular package instead:
    - Entry point: ai_history_cli.py
    - Package: ai_history/

This file contains duplicate implementations of extractors that are now in:
    - ai_history/extractors/claude_code.py
    - ai_history/extractors/cursor.py
    - ai_history/extractors/gemini.py
    - ai_history/extractors/warp.py
    - ai_history/extractors/copilot.py

Migration guide:
    - Old: python ai-history.py list
    - New: ai-history list

See README.md for updated usage instructions.
"""

"""
ai-history - Local AI Chat History Exporter

A local alternative to SpecStory that collects, unifies and exports chat histories
from multiple AI coding assistants without any cloud connectivity.

Supported tools:
- Claude Code
- Cursor
- VSCode Copilot
- Gemini CLI
- Warp Terminal
- Codex CLI

Usage:
    ai-history list [--tool TOOL] [--since DURATION] [--format FORMAT]
    ai-history export [--all] [--tool TOOL] [--project PATH]
    ai-history search QUERY [--tool TOOL] [--context N]
    ai-history stats
    ai-history watch [--interval SECS] [--git]
"""

import argparse
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple


# =============================================================================
# Data Models
# =============================================================================


class Tool(Enum):
    CLAUDE_CODE = "claude-code"
    CURSOR = "cursor"
    VSCODE_COPILOT = "vscode-copilot"
    COPILOT_CLI = "copilot-cli"
    GEMINI_CLI = "gemini-cli"
    WARP = "warp"
    CODEX = "codex"


class Role(Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"
    INFO = "info"


@dataclass
class UnifiedMessage:
    """Single message in a conversation."""

    role: Role
    content: str
    timestamp: datetime
    message_id: Optional[str] = None
    model: Optional[str] = None
    tokens: Optional[Dict[str, int]] = None
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    reasoning: Optional[str] = None


@dataclass
class UnifiedSession:
    """A complete conversation session."""

    tool: Tool
    session_id: str
    created_at: datetime
    last_updated: datetime
    messages: List[UnifiedMessage] = field(default_factory=list)
    project_path: Optional[str] = None
    project_hash: Optional[str] = None
    title: Optional[str] = None
    summary: Optional[str] = None
    cli_version: Optional[str] = None
    git_branch: Optional[str] = None
    source_path: Optional[str] = None

    @property
    def message_count(self) -> int:
        return len(self.messages)

    @property
    def total_tokens(self) -> Optional[int]:
        total = 0
        for msg in self.messages:
            if msg.tokens and "total" in msg.tokens:
                total += msg.tokens["total"]
        return total if total > 0 else None


# =============================================================================
# Base Extractor
# =============================================================================


class BaseExtractor(ABC):
    """Base class for all tool-specific extractors."""

    @property
    @abstractmethod
    def tool(self) -> Tool:
        pass

    @abstractmethod
    def extract_sessions(self) -> Iterator[UnifiedSession]:
        pass

    def is_available(self) -> bool:
        """Check if the tool's data is available on this system."""
        return True


# =============================================================================
# Claude Code Extractor
# =============================================================================


class ClaudeCodeExtractor(BaseExtractor):
    """Extract chat history from Claude Code."""

    def __init__(self):
        self.base_path = Path.home() / ".claude" / "projects"

    @property
    def tool(self) -> Tool:
        return Tool.CLAUDE_CODE

    def is_available(self) -> bool:
        return self.base_path.exists()

    def _decode_project_name(self, encoded: str) -> str:
        """Decode project path from directory name.

        Claude Code encodes paths by replacing / with -.
        E.g., /home/user/projects/my-app -> -home-user-projects-my-app

        We try to find the actual path by testing if directories exist.
        """
        if not encoded.startswith("-"):
            return encoded

        # Remove leading dash and split by dash
        parts = encoded[1:].split("-")

        # Try to reconstruct the path by testing which combinations exist
        # Start from the beginning and greedily match existing directories
        result_parts = []
        current = ""

        for i, part in enumerate(parts):
            if current:
                test_path = current + "-" + part
            else:
                test_path = part

            # Check if this could be the next path segment
            if result_parts:
                full_test = "/" + "/".join(result_parts) + "/" + test_path
            else:
                full_test = "/" + test_path

            if os.path.exists(full_test):
                result_parts.append(test_path)
                current = ""
            else:
                current = test_path

        # Add any remaining part
        if current:
            result_parts.append(current)

        if result_parts:
            return "/" + "/".join(result_parts)

        # Fallback: simple replacement
        return "/" + encoded[1:].replace("-", "/")

    def _parse_timestamp(self, ts: str) -> datetime:
        """Parse ISO timestamp."""
        try:
            # Handle various formats
            ts = ts.replace("Z", "+00:00")
            if "." in ts:
                # Truncate microseconds if too long
                parts = ts.split(".")
                if len(parts[1]) > 6:
                    ts = parts[0] + "." + parts[1][:6] + parts[1][-6:]
            return datetime.fromisoformat(ts)
        except Exception:
            return datetime.now()

    def extract_sessions(self) -> Iterator[UnifiedSession]:
        if not self.is_available():
            return

        for project_dir in self.base_path.iterdir():
            if not project_dir.is_dir():
                continue

            project_path = self._decode_project_name(project_dir.name)

            for jsonl_file in project_dir.glob("*.jsonl"):
                try:
                    yield self._parse_session(jsonl_file, project_path)
                except Exception as e:
                    print(
                        f"Warning: Failed to parse {jsonl_file}: {e}", file=sys.stderr
                    )

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
                    summary = record.get("summary")
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
                                    # Also add tool use as text for display
                                    tool_name = item.get("name", "Unknown")
                                    tool_input = item.get("input", {})
                                    if isinstance(tool_input, dict):
                                        # Format tool call nicely
                                        if tool_name == "Bash":
                                            cmd = tool_input.get("command", "")
                                            text_parts.append(
                                                f"[Tool: {tool_name}]\n```bash\n{cmd}\n```"
                                            )
                                        elif tool_name in ("Read", "Write", "Edit"):
                                            file_path = tool_input.get("file_path", "")
                                            text_parts.append(
                                                f"[Tool: {tool_name}] {file_path}"
                                            )
                                        elif tool_name == "Glob":
                                            pattern = tool_input.get("pattern", "")
                                            text_parts.append(
                                                f"[Tool: {tool_name}] {pattern}"
                                            )
                                        elif tool_name == "Grep":
                                            pattern = tool_input.get("pattern", "")
                                            text_parts.append(
                                                f"[Tool: {tool_name}] {pattern}"
                                            )
                                        else:
                                            text_parts.append(f"[Tool: {tool_name}]")
                                elif item.get("type") == "tool_result":
                                    # Tool results
                                    tool_id = item.get("tool_use_id", "")
                                    result_content = item.get("content", "")
                                    if (
                                        isinstance(result_content, str)
                                        and len(result_content) > 500
                                    ):
                                        result_content = result_content[:500] + "..."
                                    text_parts.append(
                                        f"[Tool Result]\n{result_content}"
                                    )
                            elif isinstance(item, str):
                                text_parts.append(item)
                        content = "\n".join(text_parts)
                    else:
                        tool_calls = []

                    timestamp = self._parse_timestamp(record.get("timestamp", ""))

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
            title=summary,
            summary=summary,
            cli_version=cli_version,
            git_branch=git_branch,
            source_path=str(path),
        )


# =============================================================================
# Gemini CLI Extractor
# =============================================================================


class GeminiCLIExtractor(BaseExtractor):
    """Extract chat history from Gemini CLI."""

    def __init__(self):
        self.base_path = Path.home() / ".gemini" / "tmp"
        self._hash_to_path: Dict[str, str] = {}
        self._build_hash_map()

    @property
    def tool(self) -> Tool:
        return Tool.GEMINI_CLI

    def is_available(self) -> bool:
        return self.base_path.exists()

    def _build_hash_map(self):
        """Build hash->path mapping by scanning known project locations."""
        project_roots = [
            Path.home() / "projects",
            Path.home() / "work",
            Path.home() / "code",
            Path.home(),
        ]

        for root in project_roots:
            if root.exists():
                try:
                    for item in root.iterdir():
                        if item.is_dir():
                            path_str = str(item.absolute())
                            hash_val = hashlib.sha256(path_str.encode()).hexdigest()
                            self._hash_to_path[hash_val] = path_str
                except PermissionError:
                    continue

    def _resolve_hash(self, hash_val: str) -> Optional[str]:
        """Resolve project hash to path."""
        return self._hash_to_path.get(hash_val)

    def _parse_timestamp(self, ts: str) -> datetime:
        """Parse ISO timestamp."""
        try:
            ts = ts.replace("Z", "+00:00")
            return datetime.fromisoformat(ts)
        except Exception:
            return datetime.now()

    def extract_sessions(self) -> Iterator[UnifiedSession]:
        if not self.is_available():
            return

        for project_dir in self.base_path.iterdir():
            if not project_dir.is_dir():
                continue
            if len(project_dir.name) != 64:  # SHA256 hash
                continue

            project_path = self._resolve_hash(project_dir.name)
            chats_dir = project_dir / "chats"

            if chats_dir.exists():
                for session_file in chats_dir.glob("session-*.json"):
                    try:
                        yield self._parse_session_file(
                            session_file, project_path, project_dir.name
                        )
                    except Exception as e:
                        print(
                            f"Warning: Failed to parse {session_file}: {e}",
                            file=sys.stderr,
                        )

    def _parse_session_file(
        self, path: Path, project_path: Optional[str], project_hash: str
    ) -> UnifiedSession:
        """Parse a single Gemini session file."""
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            data = json.load(f)

        messages = []
        for msg in data.get("messages", []):
            msg_type = msg.get("type", "")
            if msg_type in ("user", "gemini"):
                role = Role.USER if msg_type == "user" else Role.ASSISTANT
            elif msg_type == "info":
                role = Role.INFO
            else:
                continue

            thoughts = msg.get("thoughts", [])
            reasoning = None
            if thoughts:
                reasoning = "\n\n".join(
                    f"**{t.get('subject', 'Thought')}**: {t.get('description', '')}"
                    for t in thoughts
                )

            # Extract content, including tool calls if content is empty
            content = msg.get("content", "")
            tool_calls = msg.get("toolCalls", [])

            if not content and tool_calls:
                # Format tool calls as readable content
                tool_parts = []
                for tc in tool_calls:
                    tool_name = tc.get("name", tc.get("displayName", "Unknown"))
                    tool_args = tc.get("args", {})
                    tool_result = tc.get("result", [])

                    # Format the tool call
                    if tool_name in ("read_file", "ReadFile"):
                        file_path = tool_args.get("file_path", "")
                        tool_parts.append(f"[Tool: Read] {file_path}")
                    elif tool_name in ("write_file", "WriteFile"):
                        file_path = tool_args.get("file_path", "")
                        tool_parts.append(f"[Tool: Write] {file_path}")
                    elif tool_name in ("run_terminal_cmd", "Bash"):
                        cmd = tool_args.get("command", tool_args.get("cmd", ""))
                        tool_parts.append(f"[Tool: Bash]\n```bash\n{cmd}\n```")
                    elif tool_name in ("web_fetch", "WebFetch"):
                        prompt = tool_args.get("prompt", "")[:200]
                        tool_parts.append(f"[Tool: WebFetch] {prompt}...")
                    elif tool_name in ("web_search", "WebSearch"):
                        query = tool_args.get("query", "")
                        tool_parts.append(f"[Tool: WebSearch] {query}")
                    elif tool_name == "edit_file":
                        file_path = tool_args.get("file_path", "")
                        tool_parts.append(f"[Tool: Edit] {file_path}")
                    elif tool_name == "list_dir":
                        path = tool_args.get("dir_path", tool_args.get("path", "."))
                        tool_parts.append(f"[Tool: ListDir] {path}")
                    elif tool_name == "glob":
                        pattern = tool_args.get("pattern", "")
                        tool_parts.append(f"[Tool: Glob] {pattern}")
                    elif tool_name == "grep":
                        pattern = tool_args.get("pattern", "")
                        tool_parts.append(f"[Tool: Grep] {pattern}")
                    else:
                        # Generic tool formatting
                        args_str = ", ".join(
                            f"{k}={v}" for k, v in list(tool_args.items())[:3]
                        )
                        tool_parts.append(f"[Tool: {tool_name}] {args_str}")

                content = "\n\n".join(tool_parts)

            # Also append reasoning/thoughts to content if present
            if reasoning and not content:
                content = reasoning
            elif reasoning and content:
                content = f"{content}\n\n---\n**Thoughts:**\n{reasoning}"

            messages.append(
                UnifiedMessage(
                    role=role,
                    content=content,
                    timestamp=self._parse_timestamp(msg.get("timestamp", "")),
                    message_id=msg.get("id"),
                    model=msg.get("model"),
                    tokens=msg.get("tokens"),
                    reasoning=reasoning,
                )
            )

        return UnifiedSession(
            tool=Tool.GEMINI_CLI,
            session_id=data.get("sessionId", path.stem),
            created_at=self._parse_timestamp(data.get("startTime", "")),
            last_updated=self._parse_timestamp(data.get("lastUpdated", "")),
            messages=messages,
            project_path=project_path,
            project_hash=project_hash,
            source_path=str(path),
        )


# =============================================================================
# Codex CLI Extractor
# =============================================================================


class CodexExtractor(BaseExtractor):
    """Extract chat history from OpenAI Codex CLI."""

    def __init__(self):
        self.base_path = Path.home() / ".codex"

    @property
    def tool(self) -> Tool:
        return Tool.CODEX

    def is_available(self) -> bool:
        return self.base_path.exists()

    def _parse_timestamp(self, ts) -> datetime:
        """Parse timestamp (can be string or int)."""
        if isinstance(ts, int):
            return datetime.fromtimestamp(ts)
        try:
            ts = str(ts).replace("Z", "+00:00")
            return datetime.fromisoformat(ts)
        except Exception:
            return datetime.now()

    def extract_sessions(self) -> Iterator[UnifiedSession]:
        if not self.is_available():
            return

        sessions_dir = self.base_path / "sessions"
        if not sessions_dir.exists():
            return

        for year_dir in sessions_dir.iterdir():
            if not year_dir.is_dir():
                continue
            for month_dir in year_dir.iterdir():
                if not month_dir.is_dir():
                    continue
                for day_dir in month_dir.iterdir():
                    if not day_dir.is_dir():
                        continue
                    for session_file in day_dir.glob("rollout-*.jsonl"):
                        try:
                            yield self._parse_session_file(session_file)
                        except Exception as e:
                            print(
                                f"Warning: Failed to parse {session_file}: {e}",
                                file=sys.stderr,
                            )

    def _parse_session_file(self, path: Path) -> UnifiedSession:
        """Parse a single Codex session file."""
        messages = []
        metadata = {}
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
                timestamp = self._parse_timestamp(record.get("timestamp", ""))

                if created_at is None or timestamp < created_at:
                    created_at = timestamp
                if last_updated is None or timestamp > last_updated:
                    last_updated = timestamp

                if record_type == "session_meta":
                    metadata = record.get("payload", {})
                elif record_type == "message":
                    payload = record.get("payload", {})
                    role_str = payload.get("role", "user")
                    role = Role.USER if role_str == "user" else Role.ASSISTANT

                    content = payload.get("content", "")
                    if isinstance(content, list):
                        text_parts = []
                        for item in content:
                            if isinstance(item, dict) and item.get("type") == "text":
                                text_parts.append(item.get("text", ""))
                        content = "\n".join(text_parts)

                    messages.append(
                        UnifiedMessage(
                            role=role,
                            content=content,
                            timestamp=timestamp,
                            message_id=payload.get("id"),
                        )
                    )
                elif record_type == "response_item":
                    payload = record.get("payload", {})
                    payload_type = payload.get("type", "")

                    if payload_type == "message":
                        role_str = payload.get("role", "assistant")
                        role = Role.USER if role_str == "user" else Role.ASSISTANT

                        content_list = payload.get("content", [])
                        text_parts = []
                        for item in content_list:
                            if isinstance(item, dict):
                                item_type = item.get("type", "")
                                if item_type == "output_text":
                                    text_parts.append(item.get("text", ""))
                                elif item_type == "input_text":
                                    text_parts.append(item.get("text", ""))
                        content = "\n".join(text_parts)

                        if content:
                            messages.append(
                                UnifiedMessage(
                                    role=role,
                                    content=content,
                                    timestamp=timestamp,
                                    message_id=payload.get("id"),
                                )
                            )

                    elif payload_type == "reasoning":
                        # Codex reasoning/thinking block
                        summary = payload.get("summary", [])
                        summary_text = ""
                        for s in summary:
                            if isinstance(s, dict) and s.get("type") == "summary_text":
                                summary_text = s.get("text", "")
                                break

                        if summary_text:
                            messages.append(
                                UnifiedMessage(
                                    role=Role.ASSISTANT,
                                    content=f"💭 {summary_text}",
                                    timestamp=timestamp,
                                    reasoning=summary_text,
                                )
                            )

                    elif payload_type == "function_call":
                        # Codex tool call
                        func_name = payload.get("name", "unknown")
                        func_args_str = payload.get("arguments", "{}")
                        try:
                            func_args = json.loads(func_args_str)
                        except json.JSONDecodeError:
                            func_args = {"raw": func_args_str}

                        # Format the tool call nicely
                        if func_name == "shell_command":
                            cmd = func_args.get("command", "")
                            content = f"[Tool: Bash]\n```bash\n{cmd}\n```"
                        elif func_name in ("read_file", "str_replace_editor"):
                            file_path = func_args.get(
                                "path", func_args.get("file_path", "")
                            )
                            content = f"[Tool: {func_name}] {file_path}"
                        elif func_name == "write_file":
                            file_path = func_args.get("path", "")
                            content = f"[Tool: Write] {file_path}"
                        else:
                            args_preview = ", ".join(
                                f"{k}={str(v)[:50]}"
                                for k, v in list(func_args.items())[:3]
                            )
                            content = f"[Tool: {func_name}] {args_preview}"

                        messages.append(
                            UnifiedMessage(
                                role=Role.ASSISTANT,
                                content=content,
                                timestamp=timestamp,
                                message_id=payload.get("call_id"),
                            )
                        )

        if created_at is None:
            created_at = datetime.fromtimestamp(path.stat().st_mtime)
        if last_updated is None:
            last_updated = datetime.fromtimestamp(path.stat().st_mtime)

        return UnifiedSession(
            tool=Tool.CODEX,
            session_id=metadata.get("id", path.stem),
            created_at=created_at,
            last_updated=last_updated,
            messages=messages,
            project_path=metadata.get("cwd"),
            cli_version=metadata.get("cli_version"),
            source_path=str(path),
        )


# =============================================================================
# Warp Terminal Extractor
# =============================================================================


class WarpExtractor(BaseExtractor):
    """Extract chat history from Warp Terminal."""

    def __init__(self):
        self.db_path = (
            Path.home() / ".local" / "state" / "warp-terminal" / "warp.sqlite"
        )

    @property
    def tool(self) -> Tool:
        return Tool.WARP

    def is_available(self) -> bool:
        return self.db_path.exists()

    def _parse_timestamp(self, ts) -> datetime:
        """Parse timestamp (milliseconds or ISO string)."""
        if isinstance(ts, (int, float)):
            # Could be milliseconds or seconds
            if ts > 1e12:
                ts = ts / 1000
            return datetime.fromtimestamp(ts)
        try:
            return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        except Exception:
            return datetime.now()

    def extract_sessions(self) -> Iterator[UnifiedSession]:
        if not self.is_available():
            return

        try:
            conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
        except sqlite3.Error as e:
            print(f"Warning: Could not open Warp database: {e}", file=sys.stderr)
            return

        try:
            # Extract from ai_queries table
            cursor = conn.execute(
                """
                SELECT exchange_id, conversation_id, input, working_directory,
                       start_ts, model_id
                FROM ai_queries
                ORDER BY start_ts
            """
            )

            # Group queries by conversation_id
            conversations: Dict[str, List[Dict]] = {}
            for row in cursor:
                conv_id = row["conversation_id"] or row["exchange_id"]
                if conv_id not in conversations:
                    conversations[conv_id] = []

                try:
                    input_data = json.loads(row["input"]) if row["input"] else {}
                except json.JSONDecodeError:
                    input_data = {}

                conversations[conv_id].append(
                    {
                        "input": input_data,
                        "working_directory": row["working_directory"],
                        "start_ts": row["start_ts"],
                        "model_id": row["model_id"],
                    }
                )

            for conv_id, queries in conversations.items():
                try:
                    yield self._build_session(conv_id, queries)
                except Exception as e:
                    print(
                        f"Warning: Failed to build Warp session {conv_id}: {e}",
                        file=sys.stderr,
                    )

        finally:
            conn.close()

    def _build_session(self, conv_id: str, queries: List[Dict]) -> UnifiedSession:
        """Build a session from grouped queries."""
        messages = []
        project_path = None
        created_at = None
        last_updated = None

        for query in queries:
            timestamp = self._parse_timestamp(query["start_ts"])

            if created_at is None or timestamp < created_at:
                created_at = timestamp
            if last_updated is None or timestamp > last_updated:
                last_updated = timestamp

            if project_path is None:
                project_path = query.get("working_directory")

            input_data = query.get("input", {})
            if isinstance(input_data, list) and len(input_data) > 0:
                input_data = input_data[0]

            # Extract user query text
            if isinstance(input_data, dict):
                query_obj = input_data.get("Query", {})
                text = query_obj.get("text", "")
            else:
                text = str(input_data)

            if text:
                messages.append(
                    UnifiedMessage(
                        role=Role.USER,
                        content=text,
                        timestamp=timestamp,
                        model=query.get("model_id"),
                    )
                )

        if created_at is None:
            created_at = datetime.now()
        if last_updated is None:
            last_updated = datetime.now()

        return UnifiedSession(
            tool=Tool.WARP,
            session_id=conv_id,
            created_at=created_at,
            last_updated=last_updated,
            messages=messages,
            project_path=project_path,
            source_path=str(self.db_path),
        )


# =============================================================================
# Cursor Extractor
# =============================================================================


class CursorExtractor(BaseExtractor):
    """Extract chat history from Cursor IDE."""

    def __init__(self):
        self.db_path = (
            Path.home()
            / ".config"
            / "Cursor"
            / "User"
            / "globalStorage"
            / "state.vscdb"
        )

    @property
    def tool(self) -> Tool:
        return Tool.CURSOR

    def is_available(self) -> bool:
        return self.db_path.exists()

    def _parse_timestamp(self, ts) -> datetime:
        """Parse timestamp (milliseconds)."""
        if isinstance(ts, (int, float)):
            if ts > 1e12:
                ts = ts / 1000
            return datetime.fromtimestamp(ts)
        return datetime.now()

    def extract_sessions(self) -> Iterator[UnifiedSession]:
        if not self.is_available():
            return

        try:
            conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
        except sqlite3.Error as e:
            print(f"Warning: Could not open Cursor database: {e}", file=sys.stderr)
            return

        try:
            cursor = conn.execute(
                "SELECT key, value FROM cursorDiskKV WHERE key LIKE 'composerData:%'"
            )

            for key, value in cursor:
                try:
                    composer_id = key.split(":")[-1]
                    data = json.loads(value)
                    yield self._parse_composer(composer_id, data)
                except Exception as e:
                    print(
                        f"Warning: Failed to parse Cursor composer {key}: {e}",
                        file=sys.stderr,
                    )

        finally:
            conn.close()

    def _parse_composer(self, composer_id: str, data: dict) -> UnifiedSession:
        """Parse a Cursor composer session."""
        created_at = self._parse_timestamp(data.get("createdAt", 0))
        last_updated = self._parse_timestamp(data.get("lastUpdatedAt", 0))

        # Extract project context from file selections
        project_path = None
        context = data.get("context", {})
        file_selections = context.get("fileSelections", [])
        if file_selections:
            first_file = file_selections[0] if file_selections else {}
            if isinstance(first_file, dict):
                uri = first_file.get("uri") or {}
                if isinstance(uri, dict):
                    file_path = uri.get("path", "")
                    if file_path:
                        parts = file_path.split("/")
                        if "projects" in parts:
                            idx = parts.index("projects")
                            if idx + 1 < len(parts):
                                project_path = "/".join(parts[: idx + 2])

        return UnifiedSession(
            tool=Tool.CURSOR,
            session_id=composer_id,
            created_at=created_at,
            last_updated=last_updated,
            messages=[],  # Full messages not easily accessible
            project_path=project_path,
            title=data.get("name"),
            source_path=str(self.db_path),
        )


# =============================================================================
# VSCode Copilot Extractor
# =============================================================================


class VSCodeCopilotExtractor(BaseExtractor):
    """Extract chat history from VSCode Copilot (workspace chatSessions)."""

    def __init__(self):
        self.workspace_storage = (
            Path.home() / ".config" / "Code" / "User" / "workspaceStorage"
        )

    @property
    def tool(self) -> Tool:
        return Tool.VSCODE_COPILOT

    def is_available(self) -> bool:
        return self.workspace_storage.exists()

    def _parse_timestamp(self, ts) -> datetime:
        """Parse timestamp (milliseconds)."""
        if isinstance(ts, (int, float)):
            if ts > 1e12:
                ts = ts / 1000
            return datetime.fromtimestamp(ts)
        try:
            return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        except Exception:
            return datetime.now()

    def _get_workspace_project(self, workspace_dir: Path) -> Optional[str]:
        """Try to get project path from workspace.json."""
        workspace_json = workspace_dir / "workspace.json"
        if workspace_json.exists():
            try:
                with open(workspace_json, "r") as f:
                    data = json.load(f)
                    folder = data.get("folder")
                    if folder and folder.startswith("file://"):
                        return folder[7:]  # Remove file:// prefix
            except Exception:
                pass
        return None

    def extract_sessions(self) -> Iterator[UnifiedSession]:
        if not self.is_available():
            return

        for workspace_dir in self.workspace_storage.iterdir():
            if not workspace_dir.is_dir():
                continue

            chat_sessions_dir = workspace_dir / "chatSessions"
            if not chat_sessions_dir.exists():
                continue

            project_path = self._get_workspace_project(workspace_dir)

            for session_file in chat_sessions_dir.glob("*.json"):
                try:
                    yield self._parse_session(session_file, project_path)
                except Exception as e:
                    print(
                        f"Warning: Failed to parse VSCode session {session_file}: {e}",
                        file=sys.stderr,
                    )

    def _parse_session(self, path: Path, project_path: Optional[str]) -> UnifiedSession:
        """Parse a VSCode Copilot chat session file."""
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            data = json.load(f)

        messages = []
        created_at = None
        last_updated = None

        for request in data.get("requests", []):
            # User message
            msg_data = request.get("message", {})
            user_text = msg_data.get("text", "")

            if user_text:
                timestamp = datetime.fromtimestamp(path.stat().st_mtime)
                messages.append(
                    UnifiedMessage(
                        role=Role.USER,
                        content=user_text,
                        timestamp=timestamp,
                        message_id=request.get("requestId"),
                    )
                )

                if created_at is None:
                    created_at = timestamp
                last_updated = timestamp

            # Assistant response
            response = request.get("response", [])
            for resp_item in response:
                if isinstance(resp_item, dict):
                    # Handle different response types
                    if resp_item.get("kind") == "markdownContent":
                        content = resp_item.get("content", {}).get("value", "")
                        if content:
                            messages.append(
                                UnifiedMessage(
                                    role=Role.ASSISTANT,
                                    content=content,
                                    timestamp=(
                                        timestamp
                                        if "timestamp" in dir()
                                        else datetime.now()
                                    ),
                                )
                            )

        if created_at is None:
            created_at = datetime.fromtimestamp(path.stat().st_mtime)
        if last_updated is None:
            last_updated = datetime.fromtimestamp(path.stat().st_mtime)

        return UnifiedSession(
            tool=Tool.VSCODE_COPILOT,
            session_id=path.stem,
            created_at=created_at,
            last_updated=last_updated,
            messages=messages,
            project_path=project_path,
            title=data.get("customTitle"),
            source_path=str(path),
        )


# =============================================================================
# GitHub Copilot CLI Extractor
# =============================================================================


class CopilotCLIExtractor(BaseExtractor):
    """Extract chat history from GitHub Copilot CLI."""

    def __init__(self):
        self.base_path = Path.home() / ".copilot"

    @property
    def tool(self) -> Tool:
        return Tool.COPILOT_CLI

    def is_available(self) -> bool:
        return (self.base_path / "session-state").exists()

    def _parse_timestamp(self, ts: str) -> datetime:
        """Parse ISO timestamp."""
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except Exception:
            return datetime.now()

    def extract_sessions(self) -> Iterator[UnifiedSession]:
        if not self.is_available():
            return

        session_state_dir = self.base_path / "session-state"
        for session_file in session_state_dir.glob("*.jsonl"):
            try:
                yield self._parse_session(session_file)
            except Exception as e:
                print(
                    f"Warning: Failed to parse Copilot CLI session {session_file}: {e}",
                    file=sys.stderr,
                )

    def _parse_session(self, path: Path) -> UnifiedSession:
        """Parse a Copilot CLI session file."""
        messages = []
        session_id = path.stem
        created_at = None
        last_updated = None
        project_path = None

        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue

                record_type = record.get("type", "")
                timestamp = self._parse_timestamp(record.get("timestamp", ""))

                if created_at is None or timestamp < created_at:
                    created_at = timestamp
                if last_updated is None or timestamp > last_updated:
                    last_updated = timestamp

                data = record.get("data", {})

                if record_type == "session.start":
                    session_id = data.get("sessionId", session_id)

                elif record_type == "session.info":
                    # Extract project path from folder_trust message
                    msg = data.get("message", "")
                    if "Folder" in msg and "has been added" in msg:
                        # Extract path from message like "Folder /path/to/project has been added..."
                        parts = msg.split(" ")
                        if len(parts) >= 2:
                            potential_path = parts[1]
                            if potential_path.startswith("/"):
                                project_path = potential_path

                elif record_type == "user.message":
                    content = data.get("content", "")
                    if content:
                        messages.append(
                            UnifiedMessage(
                                role=Role.USER,
                                content=content,
                                timestamp=timestamp,
                                message_id=record.get("id"),
                            )
                        )

                elif record_type == "assistant.message":
                    content = data.get("content", "")
                    tool_requests = data.get("toolRequests", [])

                    if content or tool_requests:
                        tool_calls = []
                        for tr in tool_requests:
                            tool_calls.append(
                                {
                                    "id": tr.get("toolCallId"),
                                    "name": tr.get("name"),
                                    "input": tr.get("arguments"),
                                }
                            )

                        messages.append(
                            UnifiedMessage(
                                role=Role.ASSISTANT,
                                content=content,
                                timestamp=timestamp,
                                message_id=data.get("messageId"),
                                tool_calls=tool_calls,
                            )
                        )

        if created_at is None:
            created_at = datetime.fromtimestamp(path.stat().st_mtime)
        if last_updated is None:
            last_updated = datetime.fromtimestamp(path.stat().st_mtime)

        return UnifiedSession(
            tool=Tool.COPILOT_CLI,
            session_id=session_id,
            created_at=created_at,
            last_updated=last_updated,
            messages=messages,
            project_path=project_path,
            source_path=str(path),
        )


# =============================================================================
# Markdown Exporter
# =============================================================================


class MarkdownExporter:
    """Export sessions to Markdown format."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize string for use as filename."""
        # Remove or replace invalid characters
        name = re.sub(r'[<>:"/\\|?*]', "", name)
        name = re.sub(r"\s+", "-", name)
        name = name[:50]  # Limit length
        return name or "untitled"

    def _project_to_dirname(self, project_path: Optional[str]) -> str:
        """Convert project path to directory name."""
        if not project_path:
            return "_unknown"
        # /home/user/projects/foo -> home-user-projects-foo
        clean = project_path.strip("/").replace("/", "-")
        return clean or "_unknown"

    def export_session(self, session: UnifiedSession) -> Path:
        """Export a single session to Markdown."""
        # Build output path
        project_dir = self._project_to_dirname(session.project_path)
        tool_dir = session.tool.value

        output_path = self.output_dir / "projects" / project_dir / tool_dir
        output_path.mkdir(parents=True, exist_ok=True)

        # Generate filename
        date_str = session.created_at.strftime("%Y-%m-%d")
        title_part = self._sanitize_filename(session.title or session.session_id[:8])
        filename = f"{date_str}_{title_part}.md"

        file_path = output_path / filename

        # Generate content
        content = self._generate_markdown(session)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return file_path

    def _generate_markdown(self, session: UnifiedSession) -> str:
        """Generate Markdown content for a session."""
        lines = []

        # Frontmatter
        lines.append("---")
        lines.append(f"tool: {session.tool.value}")
        lines.append(f"session_id: {session.session_id}")
        if session.project_path:
            lines.append(f"project: {session.project_path}")
        lines.append(f"created: {session.created_at.isoformat()}")
        lines.append(f"updated: {session.last_updated.isoformat()}")
        lines.append(f"messages: {session.message_count}")
        if session.total_tokens:
            lines.append(f"tokens: {session.total_tokens}")
        if session.cli_version:
            lines.append(f"cli_version: {session.cli_version}")
        if session.git_branch:
            lines.append(f"git_branch: {session.git_branch}")
        lines.append("---")
        lines.append("")

        # Title
        title = session.title or session.summary or f"Session {session.session_id[:8]}"
        lines.append(f"# {title}")
        lines.append("")

        # Metadata
        lines.append(f"**Tool:** {session.tool.value}")
        if session.cli_version:
            lines.append(f" v{session.cli_version}")
        lines.append("")
        if session.project_path:
            lines.append(f"**Project:** `{session.project_path}`")
            lines.append("")

        # Duration
        duration = session.last_updated - session.created_at
        if duration.total_seconds() > 60:
            minutes = int(duration.total_seconds() / 60)
            hours = minutes // 60
            mins = minutes % 60
            if hours > 0:
                lines.append(f"**Duration:** {hours}h {mins}m")
            else:
                lines.append(f"**Duration:** {mins}m")
            lines.append("")

        lines.append("---")
        lines.append("")
        lines.append("## Conversation")
        lines.append("")

        # Messages
        for msg in session.messages:
            role_display = msg.role.value.title()
            time_str = msg.timestamp.strftime("%H:%M:%S")

            lines.append(f"### {role_display} ({time_str})")
            lines.append("")

            if msg.role == Role.USER:
                # Quote user messages
                for line in msg.content.split("\n"):
                    lines.append(f"> {line}")
            else:
                lines.append(msg.content)

            # Tool calls
            if msg.tool_calls:
                lines.append("")
                for tc in msg.tool_calls:
                    tool_name = tc.get("name", "Unknown Tool")
                    lines.append(f"<details>")
                    lines.append(f"<summary>Tool: {tool_name}</summary>")
                    lines.append("")
                    lines.append("```json")
                    lines.append(json.dumps(tc.get("input", {}), indent=2))
                    lines.append("```")
                    lines.append("</details>")

            # Reasoning/thoughts
            if msg.reasoning:
                lines.append("")
                lines.append("<details>")
                lines.append("<summary>Reasoning</summary>")
                lines.append("")
                lines.append(msg.reasoning)
                lines.append("</details>")

            lines.append("")
            lines.append("---")
            lines.append("")

        # Statistics
        if session.message_count > 0:
            lines.append("## Statistics")
            lines.append("")
            lines.append("| Metric | Value |")
            lines.append("|--------|-------|")
            lines.append(f"| Total Messages | {session.message_count} |")

            user_msgs = sum(1 for m in session.messages if m.role == Role.USER)
            asst_msgs = sum(1 for m in session.messages if m.role == Role.ASSISTANT)
            lines.append(f"| User Messages | {user_msgs} |")
            lines.append(f"| Assistant Messages | {asst_msgs} |")

            tool_calls = sum(len(m.tool_calls) for m in session.messages)
            if tool_calls > 0:
                lines.append(f"| Tool Calls | {tool_calls} |")

            if session.total_tokens:
                lines.append(f"| Total Tokens | ~{session.total_tokens:,} |")

        return "\n".join(lines)


# =============================================================================
# Index Builder
# =============================================================================


class IndexBuilder:
    """Build search index for sessions."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.index_path = output_dir / "index.json"

    def build_index(
        self, sessions: List[UnifiedSession], export_paths: Dict[str, Path]
    ) -> None:
        """Build and save the search index."""
        index = {
            "version": "1.0.0",
            "generated_at": datetime.now().isoformat(),
            "stats": self._compute_stats(sessions),
            "sessions": [],
            "search_index": {},
        }

        keyword_index: Dict[str, List[str]] = {}

        for session in sessions:
            export_path = export_paths.get(session.session_id, "")

            # Extract keywords from content
            keywords = self._extract_keywords(session)

            session_entry = {
                "id": session.session_id,
                "tool": session.tool.value,
                "project": session.project_path,
                "title": session.title,
                "created": session.created_at.isoformat(),
                "updated": session.last_updated.isoformat(),
                "messages": session.message_count,
                "export_path": str(export_path) if export_path else None,
                "keywords": keywords,
            }
            index["sessions"].append(session_entry)

            # Build keyword index
            for kw in keywords:
                if kw not in keyword_index:
                    keyword_index[kw] = []
                keyword_index[kw].append(session.session_id)

        index["search_index"] = keyword_index

        # Save index
        self.output_dir.mkdir(parents=True, exist_ok=True)
        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2)

    def _compute_stats(self, sessions: List[UnifiedSession]) -> Dict:
        """Compute statistics from sessions."""
        by_tool: Dict[str, int] = {}
        by_project: Dict[str, int] = {}

        for session in sessions:
            tool_name = session.tool.value
            by_tool[tool_name] = by_tool.get(tool_name, 0) + 1

            if session.project_path:
                by_project[session.project_path] = (
                    by_project.get(session.project_path, 0) + 1
                )

        return {
            "total_sessions": len(sessions),
            "total_messages": sum(s.message_count for s in sessions),
            "by_tool": by_tool,
            "by_project": by_project,
        }

    def _extract_keywords(self, session: UnifiedSession) -> List[str]:
        """Extract searchable keywords from session."""
        keywords = set()

        # From title
        if session.title:
            words = re.findall(r"\b\w{3,}\b", session.title.lower())
            keywords.update(words)

        # From messages (limited to avoid huge indexes)
        for msg in session.messages[:20]:  # First 20 messages
            words = re.findall(r"\b\w{4,}\b", msg.content.lower())
            keywords.update(words[:50])  # First 50 words per message

        # Filter out common words
        stopwords = {
            "this",
            "that",
            "with",
            "have",
            "will",
            "from",
            "they",
            "been",
            "were",
            "said",
            "each",
            "which",
            "their",
            "there",
            "would",
            "about",
        }
        keywords -= stopwords

        return list(keywords)[:100]  # Limit to 100 keywords


# =============================================================================
# Search Engine
# =============================================================================


class SearchEngine:
    """Simple in-memory search engine."""

    def __init__(self, index_path: Path):
        self.index_path = index_path
        self.index = self._load_index()

    def _load_index(self) -> Dict:
        """Load index from file."""
        if not self.index_path.exists():
            return {"sessions": [], "search_index": {}}

        with open(self.index_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def search(
        self, query: str, tool: Optional[str] = None, project: Optional[str] = None
    ) -> List[Dict]:
        """Search sessions by query."""
        query_words = query.lower().split()
        results = []

        for session in self.index.get("sessions", []):
            # Filter by tool
            if tool and session.get("tool") != tool:
                continue

            # Filter by project
            if project and session.get("project") != project:
                continue

            # Score by keyword matches
            score = 0
            session_keywords = set(session.get("keywords", []))

            for word in query_words:
                if word in session_keywords:
                    score += 5
                if session.get("title") and word in session.get("title", "").lower():
                    score += 10

            if score > 0:
                results.append(
                    {
                        "session": session,
                        "score": score,
                    }
                )

        # Sort by score descending
        results.sort(key=lambda r: r["score"], reverse=True)
        return results


# =============================================================================
# CLI Interface
# =============================================================================


def parse_duration(duration_str: str) -> timedelta:
    """Parse duration string like '7d', '2w', '1m'."""
    match = re.match(r"^(\d+)([dwmh])$", duration_str.lower())
    if not match:
        raise ValueError(f"Invalid duration format: {duration_str}")

    value = int(match.group(1))
    unit = match.group(2)

    if unit == "h":
        return timedelta(hours=value)
    elif unit == "d":
        return timedelta(days=value)
    elif unit == "w":
        return timedelta(weeks=value)
    elif unit == "m":
        return timedelta(days=value * 30)

    return timedelta(days=value)


def make_naive(dt: datetime) -> datetime:
    """Convert datetime to naive (no timezone) for comparison."""
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


def get_all_extractors() -> List[BaseExtractor]:
    """Get all available extractors."""
    return [
        ClaudeCodeExtractor(),
        GeminiCLIExtractor(),
        CodexExtractor(),
        WarpExtractor(),
        CursorExtractor(),
        VSCodeCopilotExtractor(),
        CopilotCLIExtractor(),
    ]


def cmd_list(args):
    """List all sessions."""
    extractors = get_all_extractors()
    sessions = []

    for extractor in extractors:
        if args.tool and extractor.tool.value != args.tool:
            continue
        if not extractor.is_available():
            continue

        for session in extractor.extract_sessions():
            # Filter by date
            if args.since:
                cutoff = datetime.now() - parse_duration(args.since)
                if make_naive(session.created_at) < cutoff:
                    continue

            # Filter by project
            if args.project and session.project_path != args.project:
                continue

            sessions.append(session)

    # Sort by date
    sessions.sort(key=lambda s: make_naive(s.last_updated), reverse=True)

    if args.format == "json":
        output = []
        for s in sessions:
            output.append(
                {
                    "tool": s.tool.value,
                    "session_id": s.session_id,
                    "project": s.project_path,
                    "title": s.title,
                    "created": s.created_at.isoformat(),
                    "messages": s.message_count,
                }
            )
        print(json.dumps(output, indent=2))
    else:
        # Table format
        print(f"{'Tool':<15} {'Date':<12} {'Messages':>8}  {'Project/Title'}")
        print("-" * 80)
        for s in sessions:
            date_str = s.created_at.strftime("%Y-%m-%d")
            title = s.title or s.project_path or s.session_id[:20]
            if len(title) > 40:
                title = title[:37] + "..."
            print(f"{s.tool.value:<15} {date_str:<12} {s.message_count:>8}  {title}")

    print(f"\nTotal: {len(sessions)} sessions")


def cmd_export(args):
    """Export sessions to Markdown."""
    output_dir = Path(args.output_dir).expanduser()
    exporter = MarkdownExporter(output_dir)
    index_builder = IndexBuilder(output_dir)

    extractors = get_all_extractors()
    sessions = []
    export_paths: Dict[str, Path] = {}

    for extractor in extractors:
        if args.tool and extractor.tool.value != args.tool:
            continue
        if not extractor.is_available():
            continue

        print(f"Extracting from {extractor.tool.value}...")

        for session in extractor.extract_sessions():
            # Filter by project
            if args.project and session.project_path != args.project:
                continue

            sessions.append(session)

            # Export to markdown
            try:
                path = exporter.export_session(session)
                export_paths[session.session_id] = path
                print(f"  Exported: {path}")
            except Exception as e:
                print(f"  Error exporting {session.session_id}: {e}", file=sys.stderr)

    # Build index
    print("\nBuilding index...")
    index_builder.build_index(sessions, export_paths)
    print(f"Index saved to: {index_builder.index_path}")

    print(f"\nExported {len(sessions)} sessions to {output_dir}")


def cmd_search(args):
    """Search across sessions."""
    output_dir = Path(args.output_dir).expanduser()
    engine = SearchEngine(output_dir / "index.json")

    results = engine.search(args.query, tool=args.tool, project=args.project)

    if not results:
        print("No results found.")
        return

    print(f"Found {len(results)} results for '{args.query}':\n")

    for r in results[:20]:  # Show top 20
        session = r["session"]
        score = r["score"]
        print(f"[{session['tool']}] {session.get('title', session['id'][:20])}")
        print(
            f"  Score: {score} | Date: {session['created'][:10]} | Messages: {session['messages']}"
        )
        if session.get("export_path"):
            print(f"  File: {session['export_path']}")
        print()


def cmd_stats(args):
    """Show statistics."""
    output_dir = Path(args.output_dir).expanduser()
    index_path = output_dir / "index.json"

    if not index_path.exists():
        print("No index found. Run 'ai-history export --all' first.")
        return

    with open(index_path, "r", encoding="utf-8") as f:
        index = json.load(f)

    stats = index.get("stats", {})

    print("AI History Statistics")
    print("=" * 40)
    print(f"Total Sessions: {stats.get('total_sessions', 0)}")
    print(f"Total Messages: {stats.get('total_messages', 0)}")
    print(f"Generated: {index.get('generated_at', 'Unknown')}")
    print()

    print("Sessions by Tool:")
    for tool, count in stats.get("by_tool", {}).items():
        print(f"  {tool}: {count}")
    print()

    print("Top Projects:")
    projects = stats.get("by_project", {})
    sorted_projects = sorted(projects.items(), key=lambda x: x[1], reverse=True)
    for project, count in sorted_projects[:10]:
        print(f"  {project}: {count}")


def cmd_watch(args):
    """Watch for new sessions and auto-export."""
    output_dir = Path(args.output_dir).expanduser()
    exporter = MarkdownExporter(output_dir)
    index_builder = IndexBuilder(output_dir)

    print(f"Watching for new sessions (interval: {args.interval}s)")
    print("Press Ctrl+C to stop.\n")

    # Track known session IDs
    known_sessions: set = set()

    # Initial scan
    extractors = get_all_extractors()
    for extractor in extractors:
        if not extractor.is_available():
            continue
        for session in extractor.extract_sessions():
            known_sessions.add(session.session_id)

    print(f"Found {len(known_sessions)} existing sessions.\n")

    while True:
        try:
            time.sleep(args.interval)

            new_sessions = []
            for extractor in extractors:
                if not extractor.is_available():
                    continue
                for session in extractor.extract_sessions():
                    if session.session_id not in known_sessions:
                        new_sessions.append(session)
                        known_sessions.add(session.session_id)

            if new_sessions:
                print(
                    f"\n[{datetime.now().strftime('%H:%M:%S')}] Found {len(new_sessions)} new session(s)"
                )

                export_paths: Dict[str, Path] = {}
                for session in new_sessions:
                    try:
                        path = exporter.export_session(session)
                        export_paths[session.session_id] = path
                        print(
                            f"  Exported: {session.tool.value} - {session.title or session.session_id[:8]}"
                        )
                    except Exception as e:
                        print(f"  Error: {e}", file=sys.stderr)

                # Update index
                all_sessions = []
                for extractor in extractors:
                    if not extractor.is_available():
                        continue
                    all_sessions.extend(extractor.extract_sessions())
                index_builder.build_index(all_sessions, export_paths)

                # Git commit if requested
                if args.git:
                    try:
                        subprocess.run(
                            ["git", "-C", str(output_dir), "add", "."],
                            capture_output=True,
                            check=True,
                        )
                        msg = f"Auto-export: {len(new_sessions)} new session(s)"
                        subprocess.run(
                            ["git", "-C", str(output_dir), "commit", "-m", msg],
                            capture_output=True,
                            check=True,
                        )
                        print(f"  Git commit: {msg}")
                    except subprocess.CalledProcessError:
                        pass  # Not a git repo or nothing to commit

        except KeyboardInterrupt:
            print("\nStopped watching.")
            break


def main():
    parser = argparse.ArgumentParser(
        description="ai-history - Local AI Chat History Exporter",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ai-history list                      List all sessions
  ai-history list --tool claude-code   List Claude Code sessions only
  ai-history export --all              Export all sessions to ~/.ai-history
  ai-history search "docker"           Search for "docker" in all sessions
  ai-history watch --git               Watch for new sessions and auto-commit
        """,
    )

    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument(
        "--output-dir",
        default="~/.ai-history",
        help="Output directory (default: ~/.ai-history)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # list command
    list_parser = subparsers.add_parser("list", help="List all sessions")
    list_parser.add_argument("--tool", help="Filter by tool")
    list_parser.add_argument("--project", help="Filter by project path")
    list_parser.add_argument("--since", help="Filter by date (e.g., 7d, 2w)")
    list_parser.add_argument("--format", choices=["table", "json"], default="table")

    # export command
    export_parser = subparsers.add_parser("export", help="Export sessions to Markdown")
    export_parser.add_argument("--all", action="store_true", help="Export all sessions")
    export_parser.add_argument("--tool", help="Export only specific tool")
    export_parser.add_argument("--project", help="Export only specific project")

    # search command
    search_parser = subparsers.add_parser("search", help="Search sessions")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--tool", help="Search only specific tool")
    search_parser.add_argument("--project", help="Search only specific project")

    # stats command
    subparsers.add_parser("stats", help="Show statistics")

    # watch command
    watch_parser = subparsers.add_parser("watch", help="Watch for new sessions")
    watch_parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Poll interval in seconds (default: 60)",
    )
    watch_parser.add_argument(
        "--git", action="store_true", help="Auto-commit new exports to git"
    )

    args = parser.parse_args()

    if args.command == "list":
        cmd_list(args)
    elif args.command == "export":
        cmd_export(args)
    elif args.command == "search":
        cmd_search(args)
    elif args.command == "stats":
        cmd_stats(args)
    elif args.command == "watch":
        cmd_watch(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
