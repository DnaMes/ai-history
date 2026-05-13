import json
from pathlib import Path

from ..core.models import Role, UnifiedSession
from ..utils.paths import project_to_dirname, sanitize_filename


class MarkdownExporter:
    """Export sessions to Markdown format."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir

    def _candidate_path(self, session: UnifiedSession) -> Path:
        """Return the output path for a session without writing anything."""
        project_dir = project_to_dirname(session.project_path)
        tool_dir = session.tool.value
        date_str = session.created_at.strftime("%Y-%m-%d")
        title_part = sanitize_filename(session.title or session.session_id[:8])
        session_suffix = sanitize_filename(session.session_id)[-12:]
        filename = f"{date_str}_{title_part}_{session_suffix}.md"
        return self.output_dir / "projects" / project_dir / tool_dir / filename

    def export_session(self, session: UnifiedSession, force: bool = False) -> Path:
        """Export a single session to Markdown. Skips if file is up-to-date."""
        # Build output path
        project_dir = project_to_dirname(session.project_path)
        tool_dir = session.tool.value

        output_path = self.output_dir / "projects" / project_dir / tool_dir
        output_path.mkdir(parents=True, exist_ok=True)

        # Generate filename
        date_str = session.created_at.strftime("%Y-%m-%d")
        title_part = sanitize_filename(session.title or session.session_id[:8])
        session_suffix = sanitize_filename(session.session_id)[-12:]
        filename = f"{date_str}_{title_part}_{session_suffix}.md"

        file_path = output_path / filename

        # Skip if file exists and session hasn't been updated since last export
        if not force and file_path.exists():
            file_mtime = file_path.stat().st_mtime
            session_updated_ts = session.last_updated.timestamp()
            if file_mtime >= session_updated_ts:
                return file_path

        # Generate content
        content = self._generate_markdown(session)

        import os

        tmp = file_path.with_suffix(".tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp, file_path)
        except Exception:
            tmp.unlink(missing_ok=True)
            raise

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
        if session.thread_id:
            lines.append(f"thread_id: {session.thread_id}")
        lines.append(f"created: {session.created_at.isoformat()}")
        lines.append(f"updated: {session.last_updated.isoformat()}")
        lines.append(f"messages: {session.message_count}")
        if session.total_tokens:
            lines.append(f"tokens: {session.total_tokens}")
        if session.cli_version:
            lines.append(f"cli_version: {session.cli_version}")
        if session.git_branch:
            lines.append(f"git_branch: {session.git_branch}")
        if getattr(session, "git_commit", None):
            lines.append(f"git_commit: {session.git_commit}")
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
                    lines.append("<details>")
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
