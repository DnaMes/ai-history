import json
import hashlib
import logging
import os
import sys
from pathlib import Path
from collections import deque
from typing import Iterator, Dict, Optional
from datetime import datetime

from .base import BaseExtractor
from ..core.models import Tool, Role, UnifiedSession, UnifiedMessage
from ..utils.datetime import parse_timestamp
from ..utils.home_discovery import discover_home_marker_paths
from ..utils.paths import make_thread_id
from ..utils.security import sanitize_path


logger = logging.getLogger(__name__)


class GeminiCLIExtractor(BaseExtractor):
    """Extract chat history from Gemini CLI."""

    def __init__(self):
        self.base_path = Path.home() / ".gemini" / "tmp"
        self.base_paths = self._discover_base_paths()
        self._hash_to_path: Dict[str, str] = {}
        self._build_hash_map()

    def _discover_base_paths(self):
        paths = [self.base_path]
        for candidate in discover_home_marker_paths(".gemini/tmp"):
            if candidate not in paths:
                paths.append(candidate)
        return [path for path in paths if path.exists()]

    @property
    def tool(self) -> Tool:
        return Tool.GEMINI_CLI

    def is_available(self) -> bool:
        return len(self.base_paths) > 0

    def _build_hash_map(self):
        """Build hash->path mapping by scanning known project locations."""
        project_roots = []
        env_roots = os.environ.get("GEMINI_PROJECT_ROOTS")
        if env_roots:
            for raw in env_roots.split(os.pathsep):
                value = raw.strip()
                if not value:
                    continue
                try:
                    project_roots.append(
                        sanitize_path(value, Path.home(), allow_absolute=True)
                    )
                except ValueError as exc:
                    logger.warning(
                        "Ignoring unsafe GEMINI_PROJECT_ROOTS path '%s': %s", value, exc
                    )

        project_roots.extend(
            [
                Path.home() / "projects",
                Path.home() / "work",
                Path.home() / "code",
                Path.home(),
            ]
        )

        for root in project_roots:
            if not root.exists():
                continue
            try:
                self._scan_root(root, max_depth=3, max_dirs=2000)
            except PermissionError:
                continue

    def _scan_root(self, root: Path, max_depth: int = 2, max_dirs: int = 1000) -> None:
        queue = deque([(root, 0)])
        seen = 0
        while queue:
            current, depth = queue.popleft()
            try:
                if current.is_dir():
                    path_str = str(current.absolute())
                    hash_val = hashlib.sha256(path_str.encode()).hexdigest()
                    self._hash_to_path[hash_val] = path_str
                    seen += 1
            except PermissionError:
                continue

            if depth >= max_depth or seen >= max_dirs:
                continue

            try:
                for item in current.iterdir():
                    if item.is_dir():
                        queue.append((item, depth + 1))
            except PermissionError:
                continue

    def _resolve_hash(self, hash_val: str) -> Optional[str]:
        """Resolve project hash to path."""
        return self._hash_to_path.get(hash_val)

    def extract_sessions(self) -> Iterator[UnifiedSession]:
        if not self.is_available():
            return

        for base_path in self.base_paths:
            for project_dir in base_path.iterdir():
                if not project_dir.is_dir():
                    continue
                if len(project_dir.name) != 64:
                    continue

                project_path = self._resolve_hash(project_dir.name)
                chats_dir = project_dir / "chats"

                if chats_dir.exists():
                    for session_file in chats_dir.glob("session-*.json"):
                        try:
                            session = self._parse_session_file(
                                session_file, project_path, project_dir.name
                            )
                            if self.should_import_session(session):
                                yield session
                        except Exception as e:
                            logger.warning("Failed to parse %s: %s", session_file, e)

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
                    timestamp=parse_timestamp(msg.get("timestamp", "")),
                    message_id=msg.get("id"),
                    model=msg.get("model"),
                    tokens=msg.get("tokens"),
                    reasoning=reasoning,
                )
            )

        return UnifiedSession(
            tool=Tool.GEMINI_CLI,
            session_id=data.get("sessionId", path.stem),
            created_at=parse_timestamp(data.get("startTime", "")),
            last_updated=parse_timestamp(data.get("lastUpdated", "")),
            messages=messages,
            project_path=project_path,
            project_hash=project_hash,
            thread_id=make_thread_id(
                project_path=project_path, project_hash=project_hash
            ),
            source_path=str(path),
        )
