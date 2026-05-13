import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from ...core.models import UnifiedSession

from ..base import LLMProvider


@dataclass
class KnowledgeEntry:
    session_id: str
    topic: str
    key_points: List[str]
    code_snippets: List[str] = field(default_factory=list)
    decisions: List[str] = field(default_factory=list)
    tools_used: List[str] = field(default_factory=list)
    project: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "topic": self.topic,
            "key_points": self.key_points,
            "code_snippets": self.code_snippets,
            "decisions": self.decisions,
            "tools_used": self.tools_used,
            "project": self.project,
            "timestamp": self.timestamp.isoformat(),
        }


class KnowledgeExtractor:
    def __init__(self, provider: LLMProvider, output_dir: Optional[Path] = None):
        self.provider = provider
        self.output_dir = output_dir or Path.home() / ".ai-history" / "knowledge"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def extract_from_session(
        self,
        session: "UnifiedSession",
        max_messages: int = 20,
    ) -> Optional[KnowledgeEntry]:
        if not self.provider.is_available():
            return None

        messages = session.messages[:max_messages]
        conversation = []
        for msg in messages:
            role = msg.role.value.upper()
            content = (msg.content or "")[:500]
            conversation.append(f"{role}: {content}")

        conversation_text = "\n".join(conversation)

        prompt = f"""Extract structured knowledge from this AI coding session.

Tool: {session.tool.value}
Project: {session.project_path or "Unknown"}
Date: {session.created_at.date()}

Conversation:
{conversation_text}

Extract:
1. Main topic/goal (one sentence)
2. Key points learned (3-5 bullet points)
3. Code snippets (important code shown, max 3)
4. Decisions made (architectural, design choices)
5. Tools/technologies mentioned

Format as JSON:
{{
  "topic": "...",
  "key_points": ["...", "..."],
  "code_snippets": ["...", "..."],
  "decisions": ["...", "..."],
  "tools_used": ["...", "..."]
}}"""

        try:
            response = self.provider.generate(prompt, temperature=0.2)
            content = response.content.strip()

            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
                if content.startswith("json"):
                    content = content[4:].strip()

            data = json.loads(content)

            return KnowledgeEntry(
                session_id=session.session_id,
                topic=data.get("topic", "Unknown"),
                key_points=data.get("key_points", []),
                code_snippets=data.get("code_snippets", []),
                decisions=data.get("decisions", []),
                tools_used=data.get("tools_used", []),
                project=session.project_path,
            )

        except Exception:
            return None

    def extract_from_sessions(
        self,
        sessions: List["UnifiedSession"],
        limit: int = 50,
    ) -> List[KnowledgeEntry]:
        entries = []
        for session in sessions[:limit]:
            entry = self.extract_from_session(session)
            if entry:
                entries.append(entry)
        return entries

    def build_knowledge_base(
        self,
        entries: List[KnowledgeEntry],
        filename: str = "knowledge_base.json",
    ) -> Path:
        knowledge_base = {
            "version": "1.0",
            "created": datetime.now().isoformat(),
            "total_entries": len(entries),
            "entries": [e.to_dict() for e in entries],
            "by_topic": self._group_by_topic(entries),
            "by_project": self._group_by_project(entries),
            "by_tool": self._group_by_tool(entries),
        }

        output_path = self.output_dir / filename
        with open(output_path, "w") as f:
            json.dump(knowledge_base, f, indent=2)

        return output_path

    def _group_by_topic(self, entries: List[KnowledgeEntry]) -> Dict[str, List[str]]:
        topics = {}
        for entry in entries:
            topic_key = entry.topic.lower()[:50]
            if topic_key not in topics:
                topics[topic_key] = []
            topics[topic_key].append(entry.session_id)
        return topics

    def _group_by_project(self, entries: List[KnowledgeEntry]) -> Dict[str, List[str]]:
        projects = {}
        for entry in entries:
            project = entry.project or "Unknown"
            if project not in projects:
                projects[project] = []
            projects[project].append(entry.session_id)
        return projects

    def _group_by_tool(self, entries: List[KnowledgeEntry]) -> Dict[str, List[str]]:
        tools = {}
        for entry in entries:
            for tool in entry.tools_used:
                if tool not in tools:
                    tools[tool] = []
                tools[tool].append(entry.session_id)
        return tools
