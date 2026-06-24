#!/usr/bin/env python3
"""
Export current Claude Code session for continuation in other AI tools.
Extracts the session context and provides ready-to-paste text for Gemini, Codex, etc.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from lore.utils.security import sanitize_path


def find_latest_session(project_dir: str) -> Path:
    """Find the most recently modified JSONL file."""
    # Sanitize the project directory path
    try:
        # Allow absolute paths for Claude project directories
        base_dir = Path.home() / ".claude"
        project_path = sanitize_path(project_dir, base_dir, allow_absolute=True)
    except ValueError as e:
        print(f"❌ Invalid project directory: {e}")
        sys.exit(1)

    if not project_path.exists():
        print(f"❌ Project directory not found: {project_path}")
        sys.exit(1)

    # Find all .jsonl files (exclude subagents)
    jsonl_files = [f for f in project_path.glob("*.jsonl") if f.is_file()]

    if not jsonl_files:
        print(f"❌ No session files found in {project_path}")
        sys.exit(1)

    # Get the most recent one
    latest = max(jsonl_files, key=lambda f: f.stat().st_mtime)
    return latest


def export_session(session_file: Path, context_messages: int = 10):
    """Export session to markdown with context for other AI tools."""
    # Validate session file path
    try:
        base_dir = Path.home() / ".claude"
        validated_session = sanitize_path(str(session_file), base_dir, allow_absolute=True)
    except ValueError as e:
        print(f"❌ Invalid session file path: {e}")
        sys.exit(1)

    messages = []
    with open(validated_session) as f:
        for line in f:
            if line.strip():
                messages.append(json.loads(line))

    print(f"\n{'=' * 60}")
    print(f"Session Export: {session_file.name}")
    print(f"{'=' * 60}\n")
    print(f"Total messages: {len(messages)}")
    print(f"Exporting last {context_messages} messages...\n")

    # Get last N messages for context
    recent_messages = messages[-context_messages:] if len(messages) > context_messages else messages

    # Build export text
    export_lines = []
    export_lines.append("# Continue from Claude Code Session")
    export_lines.append(f"\n**Session:** {session_file.stem}")
    export_lines.append(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    export_lines.append(f"**Project:** {session_file.parent.name}")
    export_lines.append("\n---\n")
    export_lines.append("## Context from previous conversation:\n")

    for msg in recent_messages:
        role = msg.get("role", "unknown")

        # Extract content based on message structure
        content = ""
        if isinstance(msg.get("content"), str):
            content = msg["content"]
        elif isinstance(msg.get("content"), list):
            # Handle structured content
            parts = []
            for item in msg["content"]:
                if isinstance(item, dict):
                    if item.get("type") == "text":
                        parts.append(item.get("text", ""))
                    elif item.get("type") == "tool_use":
                        parts.append(f"[Used tool: {item.get('name')}]")
                    elif item.get("type") == "tool_result":
                        # Skip tool results in export
                        pass
                elif isinstance(item, str):
                    parts.append(item)
            content = "\n".join(parts)

        if not content or len(content.strip()) < 5:
            continue

        # Format message
        if role == "user":
            export_lines.append(f"\n### 👤 User:\n{content}\n")
        else:
            # Truncate very long assistant messages
            if len(content) > 2000:
                content = content[:2000] + "\n\n[... truncated for brevity ...]"
            export_lines.append(f"\n### 🤖 Assistant:\n{content}\n")

    export_lines.append("\n---\n")
    export_lines.append("## Current Task:\n")
    export_lines.append("*[Describe what you want to continue working on]*\n")

    export_text = "\n".join(export_lines)

    # Save to file - sanitize the output path
    try:
        tmp_dir = Path("/tmp")
        # Create safe filename from session stem
        safe_filename = f"claude-export-{session_file.stem}.md"
        # Validate filename doesn't contain path traversal
        if "/" in safe_filename or "\\" in safe_filename or ".." in safe_filename:
            raise ValueError("Invalid filename pattern")
        export_file = sanitize_path(safe_filename, tmp_dir, allow_absolute=False)
    except ValueError as e:
        print(f"❌ Could not create safe export path: {e}")
        sys.exit(1)

    with open(export_file, "w") as f:
        f.write(export_text)

    print(f"✓ Export saved to: {export_file}")
    print(f"\n{'=' * 60}")
    print("How to continue in other tools:")
    print(f"{'=' * 60}\n")

    print("📝 Gemini CLI:")
    print(f"   cat {export_file} | gemini-cli\n")

    print("📝 Codex:")
    print(f"   codex --resume-from {export_file}\n")

    print("📝 VSCode Copilot Chat:")
    print("   1. Open VSCode")
    print("   2. Open Copilot Chat (Ctrl+Shift+I)")
    print(f"   3. Paste content from: {export_file}\n")

    print("📝 Cursor:")
    print("   1. Open Cursor")
    print("   2. Open Composer (Ctrl+I)")
    print(f"   3. Paste content from: {export_file}\n")

    print(f"{'=' * 60}\n")

    # Also print to stdout for piping
    return export_text


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Export Claude Code session for other AI tools")
    parser.add_argument(
        "--project",
        default="~/.claude/projects/-home-dnames-projects-spec-story-local",
        help="Claude Code project directory",
    )
    parser.add_argument(
        "--messages",
        type=int,
        default=10,
        help="Number of recent messages to export (default: 10)",
    )
    parser.add_argument("--session", help="Specific session file to export")
    parser.add_argument("--stdout", action="store_true", help="Print export to stdout (for piping)")

    args = parser.parse_args()

    if args.session:
        try:
            session_file = Path(args.session)
            base_dir = Path.home() / ".claude"
            session_file = sanitize_path(str(session_file), base_dir, allow_absolute=True)
        except ValueError as e:
            print(f"❌ Invalid session file: {e}")
            sys.exit(1)
    else:
        session_file = find_latest_session(args.project)

    export_text = export_session(session_file, args.messages)

    if args.stdout:
        print("\n" + "=" * 60)
        print(export_text)


if __name__ == "__main__":
    main()
