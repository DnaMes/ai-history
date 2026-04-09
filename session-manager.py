#!/usr/bin/env python3
"""
AI Session Manager - Seamless switching between AI tools with full context

Usage:
    ai-session list                          # Show all sessions
    ai-session switch gemini                 # Switch to Gemini with current context
    ai-session switch codex                  # Switch to Codex with current context
    ai-session continue                      # Auto-select best tool based on rate limits
"""

import argparse
import json
import os
import subprocess
import sys
import shutil
from pathlib import Path
from datetime import datetime
import importlib.util

SCRIPT_DIR = Path(__file__).resolve().parent
AI_HISTORY_PATH = SCRIPT_DIR / "ai-history.py"

if not AI_HISTORY_PATH.exists():
    AI_HISTORY_PATH = Path("/home/dnames/projects/mcp-server/ai-history/ai-history.py")

spec = importlib.util.spec_from_file_location("ai_history", AI_HISTORY_PATH)
ai_history = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ai_history)

sys.path.insert(0, str(SCRIPT_DIR))
from ai_history.utils.security import get_safe_executable

CONTEXT_FILE = Path("/tmp/ai-session-context.md")
AI_HISTORY_DIR = Path.home() / ".ai-history"


def get_current_project() -> str:
    """Detect current project directory."""
    cwd = Path.cwd()

    # Try to find git root
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.CalledProcessError, OSError, subprocess.TimeoutExpired):
        pass

    return str(cwd)


def make_naive(dt):
    """Convert datetime to naive for comparison."""
    if dt is None:
        return datetime.min
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


def get_project_sessions(project_path: str):
    """Get all sessions for current project."""
    extractors = ai_history.get_all_extractors()
    sessions = []

    for extractor in extractors:
        if not extractor.is_available():
            continue

        try:
            for session in extractor.extract_sessions():
                if session.project_path and project_path in str(session.project_path):
                    sessions.append(session)
        except (OSError, AttributeError, RuntimeError):
            continue

    # Sort by creation time
    sessions.sort(key=lambda s: make_naive(s.created_at))
    return sessions


def format_context(sessions, max_messages: int = 15) -> str:
    """Format sessions as context for new tool."""
    if not sessions:
        return "# Starting new session\n\nNo previous context available."

    lines = []
    lines.append("# Continue AI Session")
    lines.append(
        f"\n**Project:** {sessions[0].project_path if sessions else 'Unknown'}"
    )
    lines.append(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"\n---\n")

    # Get recent messages
    all_messages = []
    for session in sessions:
        for msg in session.messages:
            if msg.content and msg.content.strip():
                all_messages.append(
                    {
                        "tool": session.tool.value
                        if hasattr(session.tool, "value")
                        else str(session.tool),
                        "timestamp": msg.timestamp,
                        "role": msg.role.value,
                        "content": msg.content,
                    }
                )

    # Sort and take last N
    all_messages.sort(key=lambda m: make_naive(m["timestamp"]) or datetime.min)
    recent = all_messages[-max_messages:]

    if not recent:
        return "# Starting new session\n\nNo previous messages found."

    lines.append("## Recent conversation:\n")

    for msg in recent:
        role_icon = "👤" if msg["role"] == "user" else "🤖"
        tool = msg["tool"].replace("Tool.", "").replace("_", "-").lower()

        content = msg["content"]
        if len(content) > 1000:
            content = content[:1000] + "\n\n[... truncated ...]"

        lines.append(f"\n### {role_icon} {msg['role'].title()} `[{tool}]`\n")
        lines.append(f"{content}\n")

    lines.append("\n---\n")
    lines.append("## Continue from here\n")

    return "\n".join(lines)


def switch_to_tool(tool: str, context: str):
    """Switch to specified AI tool with context."""

    # Save context
    CONTEXT_FILE.write_text(context)

    commands = {
        "gemini": ["gemini", f"$(cat {CONTEXT_FILE})"],
        "codex": ["codex", f"@{CONTEXT_FILE}"],
        "cursor": None,  # Manual
        "vscode": None,  # Manual
        "claude": ["claude", "--continue"],
    }

    if tool not in commands:
        print(f"❌ Unknown tool: {tool}")
        print(f"Available: {', '.join(commands.keys())}")
        return False

    cmd = commands[tool]

    if cmd is None:
        # Manual tools
        print(f"\n✓ Context saved to: {CONTEXT_FILE}")
        print(f"\nTo continue in {tool.title()}:")
        if tool == "cursor":
            print("  1. Open Cursor")
            print("  2. Press Cmd/Ctrl+I")
            print(f"  3. Paste content from {CONTEXT_FILE}")
        elif tool == "vscode":
            print("  1. Open VSCode")
            print("  2. Press Ctrl+Shift+I (Copilot Chat)")
            print(f"  3. Type: @{CONTEXT_FILE}")
        return True

    print(f"\n🚀 Switching to {tool}...\n")
    print(f"Context: {CONTEXT_FILE}")
    print(f"Command: {' '.join(cmd)}\n")

    try:
        executable = get_safe_executable(tool)
        if not executable:
            print(f"❌ {tool} not found or not safe. Install it first:")
            if tool == "gemini":
                print("  npm install -g @google/generative-ai-cli")
            elif tool == "codex":
                print("  cargo install codex-cli")
            return False

        if tool == "gemini":
            subprocess.run([executable, context], shell=False, timeout=3600)
        elif tool == "codex":
            subprocess.run([executable, f"@{CONTEXT_FILE}"], shell=False, timeout=3600)
        elif tool == "claude":
            subprocess.run([executable, "--continue"], shell=False, timeout=3600)
    except FileNotFoundError:
        print(f"❌ {tool} not found. Install it first:")
        if tool == "gemini":
            print("  npm install -g @google/generative-ai-cli")
        elif tool == "codex":
            print("  cargo install codex-cli")
        return False
    except subprocess.TimeoutExpired:
        print(f"\n⏱️  {tool} session timed out after 1 hour")
        return True
    except KeyboardInterrupt:
        print("\n\n✓ Session ended")
        return True

    return True

    return True


def auto_switch():
    """Auto-select best tool based on rate limits and availability."""

    # Check Claude Code rate limit
    claude_available = True
    try:
        # Check if we're in a rate limit
        result = subprocess.run(
            ["claude", "--help"], capture_output=True, timeout=2, check=False
        )
        if b"rate limit" in result.stderr.lower():
            claude_available = False
    except (subprocess.CalledProcessError, OSError, subprocess.TimeoutExpired):
        pass

    # Priority order
    tools = ["claude", "gemini", "codex"]

    if not claude_available:
        tools = ["gemini", "codex", "claude"]

    print("🤖 Auto-selecting AI tool...\n")

    for tool in tools:
        if shutil.which(tool) or shutil.which(f"{tool}-cli"):
            print(f"✓ Selected: {tool}")
            return tool

    print("❌ No AI tools available")
    return None


def list_sessions():
    """List all sessions for current project."""
    project = get_current_project()
    sessions = get_project_sessions(project)

    print(f"\n{'=' * 60}")
    print(f"AI Sessions for: {project}")
    print(f"{'=' * 60}\n")

    if not sessions:
        print("No sessions found for this project.")
        print("\nTip: Run 'python3 ai-history.py export --all' to rebuild index")
        return

    # Group by tool
    by_tool = {}
    for s in sessions:
        tool = s.tool.value if hasattr(s.tool, "value") else str(s.tool)
        tool = tool.replace("Tool.", "").replace("_", "-").lower()
        if tool not in by_tool:
            by_tool[tool] = []
        by_tool[tool].append(s)

    for tool, tool_sessions in sorted(by_tool.items()):
        print(f"📝 {tool.upper()}: {len(tool_sessions)} sessions")

        # Show latest 3
        for session in tool_sessions[-3:]:
            created = (
                session.created_at.strftime("%Y-%m-%d %H:%M")
                if session.created_at
                else "???"
            )
            msgs = len(session.messages)
            title = session.title or session.session_id[:12]
            print(f"   • {created} | {msgs:3d} msgs | {title}")

        if len(tool_sessions) > 3:
            print(f"   ... and {len(tool_sessions) - 3} more")
        print()

    print("─" * 60)
    print(f"Total: {len(sessions)} sessions\n")


def main():
    parser = argparse.ArgumentParser(
        description="AI Session Manager - Seamless tool switching",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ai-session list                  # Show all sessions
  ai-session switch gemini         # Switch to Gemini
  ai-session switch codex          # Switch to Codex
  ai-session continue              # Auto-select best tool

Supported tools:
  - claude (Claude Code)
  - gemini (Gemini CLI)
  - codex (Codex CLI)
  - cursor (Cursor Composer - manual)
  - vscode (VSCode Copilot - manual)
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # list command
    subparsers.add_parser("list", help="List all sessions for current project")

    # switch command
    switch_parser = subparsers.add_parser("switch", help="Switch to another AI tool")
    switch_parser.add_argument(
        "tool",
        choices=["claude", "gemini", "codex", "cursor", "vscode"],
        help="AI tool to switch to",
    )
    switch_parser.add_argument(
        "--messages",
        type=int,
        default=15,
        help="Number of recent messages (default: 15)",
    )

    # continue command
    subparsers.add_parser("continue", help="Auto-select best available tool")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "list":
        list_sessions()

    elif args.command == "switch":
        project = get_current_project()
        sessions = get_project_sessions(project)

        if not sessions:
            print(f"\n⚠️  No previous sessions found for: {project}")
            print("Starting fresh session...\n")
            context = f"# New Session\n\n**Project:** {project}\n**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        else:
            print(f"\n🔍 Loading context from {len(sessions)} previous sessions...")
            context = format_context(sessions, args.messages)

        switch_to_tool(args.tool, context)

    elif args.command == "continue":
        tool = auto_switch()
        if tool:
            project = get_current_project()
            sessions = get_project_sessions(project)
            context = format_context(sessions, 15)
            switch_to_tool(tool, context)


if __name__ == "__main__":
    main()
