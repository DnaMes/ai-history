from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class Tool(Enum):
    CLAUDE_CODE = "claude-code"
    CURSOR = "cursor"
    VSCODE_COPILOT = "vscode-copilot"
    COPILOT_CLI = "copilot-cli"
    GEMINI_CLI = "gemini-cli"
    WARP = "warp"
    CODEX = "codex"
    OPENCODE = "opencode"
    ANTIGRAVITY = "antigravity"
    AIDER = "aider"


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


class TitleSource(Enum):
    """Source of the session title."""

    NATIVE = "native"  # Tool provided the title
    SUMMARY = "summary"  # Generated from summary field
    FIRST_MESSAGE = "first_message"  # Extracted from first user message
    KEYWORDS = "keywords"  # Generated via keyword extraction
    LLM = "llm"  # Generated via local LLM
    FALLBACK = "fallback"  # Generic date-based fallback


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
    thread_id: Optional[str] = None
    title: Optional[str] = None
    summary: Optional[str] = None
    cli_version: Optional[str] = None
    git_branch: Optional[str] = None
    git_commit: Optional[str] = None
    source_path: Optional[str] = None
    generated_title: Optional[str] = None
    title_source: Optional[TitleSource] = None
    todos: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def message_count(self) -> int:
        return len(self.messages)

    @property
    def user_prompt_count(self) -> int:
        return sum(
            1 for msg in self.messages if msg.role == Role.USER and (msg.content or "").strip()
        )

    @property
    def assistant_message_count(self) -> int:
        return sum(
            1 for msg in self.messages if msg.role == Role.ASSISTANT and (msg.content or "").strip()
        )

    @property
    def total_tokens(self) -> Optional[int]:
        total = 0
        for msg in self.messages:
            if msg.tokens and "total" in msg.tokens:
                total += msg.tokens["total"]
        return total if total > 0 else None
