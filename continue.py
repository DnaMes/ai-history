#!/usr/bin/env python3
"""
Continue working with a different AI tool using ai-history context.

When Claude Code hits rate limits, seamlessly switch to Gemini CLI, Codex, or other tools
while maintaining full conversation context from ai-history.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime

# Import from ai-history.py by loading it as a module
sys.path.insert(0, str(Path(__file__).parent))
import importlib.util
spec = importlib.util.spec_from_file_location("ai_history", Path(__file__).parent / "ai-history.py")
ai_history_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ai_history_module)

get_all_extractors = ai_history_module.get_all_extractors
UnifiedSession = ai_history_module.UnifiedSession

def get_project_sessions(project_path: str) -> list[UnifiedSession]:
    """Get all sessions for a specific project across all tools."""
    extractors = get_all_extractors()
    project_sessions = []

    for extractor in extractors:
        if not extractor.is_available():
            continue

        try:
            for session in extractor.extract_sessions():
                # Match project path
                if session.project_path and project_path in str(session.project_path):
                    project_sessions.append(session)
        except Exception as e:
            print(f"⚠️  Error reading {extractor.__class__.__name__}: {e}", file=sys.stderr)

    # Sort by timestamp (most recent last)
    project_sessions.sort(key=lambda s: s.created_at or datetime.min)

    return project_sessions

def format_context_for_tool(sessions: list[UnifiedSession], max_messages: int = 20) -> str:
    """Format session history as context for continuation in another tool."""

    lines = []
    lines.append("# AI Session Context")
    lines.append(f"\n**Project:** {sessions[0].project_path if sessions else 'Unknown'}")
    lines.append(f"**Previous sessions:** {len(sessions)}")
    lines.append(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("\n---\n")

    # Get recent messages across all sessions
    all_messages = []
    for session in sessions:
        for msg in session.messages:
            all_messages.append({
                'tool': session.tool,
                'timestamp': msg.timestamp,
                'role': msg.role.value,
                'content': msg.content
            })

    # Sort by timestamp and take last N
    all_messages.sort(key=lambda m: m['timestamp'] or datetime.min)
    recent = all_messages[-max_messages:] if len(all_messages) > max_messages else all_messages

    lines.append("## Recent conversation history:\n")

    for msg in recent:
        role_emoji = "👤" if msg['role'] == 'user' else "🤖"
        tool_badge = f"[{msg['tool']}]"
        time_str = msg['timestamp'].strftime('%H:%M') if msg['timestamp'] else '??:??'

        content = msg['content'] or ''

        # Truncate very long messages
        if len(content) > 1500:
            content = content[:1500] + "\n\n[... truncated ...]"

        # Skip empty messages
        if not content.strip():
            continue

        lines.append(f"\n### {role_emoji} {msg['role'].title()} {tool_badge} ({time_str})")
        lines.append(f"\n{content}\n")

    lines.append("\n---\n")
    lines.append("## Continue from here:\n")
    lines.append("*What would you like to work on next?*\n")

    return "\n".join(lines)

def continue_with_gemini(context: str, interactive: bool = True):
    """Continue conversation in Gemini CLI."""

    print("\n📝 Starting Gemini CLI with context...\n")

    # Save context to temp file
    context_file = Path("/tmp/ai-history-context.md")
    context_file.write_text(context)

    if interactive:
        # Start gemini-cli with context
        prompt = f"{context}\n\n[Continue working on this project]"
        subprocess.run(["gemini-cli", prompt])
    else:
        print(f"Context saved to: {context_file}")
        print(f"\nTo continue in Gemini CLI, run:")
        print(f"  gemini-cli \"$(cat {context_file})\"")

def continue_with_codex(context: str, interactive: bool = True):
    """Continue conversation in Codex CLI."""

    print("\n📝 Starting Codex with context...\n")

    # Save context to temp file
    context_file = Path("/tmp/ai-history-context.md")
    context_file.write_text(context)

    if interactive:
        # Start codex with context
        subprocess.run(["codex", f"@{context_file}"])
    else:
        print(f"Context saved to: {context_file}")
        print(f"\nTo continue in Codex, run:")
        print(f"  codex @{context_file}")

def continue_with_cursor(context: str):
    """Prepare context for Cursor Composer."""

    print("\n📝 Preparing context for Cursor...\n")

    context_file = Path("/tmp/ai-history-context.md")
    context_file.write_text(context)

    print(f"✓ Context saved to: {context_file}")
    print("\nTo continue in Cursor:")
    print("  1. Open Cursor in your project")
    print("  2. Press Ctrl+I (or Cmd+I) to open Composer")
    print(f"  3. Paste the content from: {context_file}")
    print(f"  4. Or type: @{context_file}")

def continue_with_vscode(context: str):
    """Prepare context for VSCode Copilot Chat."""

    print("\n📝 Preparing context for VSCode Copilot...\n")

    context_file = Path("/tmp/ai-history-context.md")
    context_file.write_text(context)

    print(f"✓ Context saved to: {context_file}")
    print("\nTo continue in VSCode Copilot Chat:")
    print("  1. Open VSCode in your project")
    print("  2. Press Ctrl+Shift+I to open Copilot Chat")
    print(f"  3. Reference the context file with: @{context_file}")

def main():
    parser = argparse.ArgumentParser(
        description="Continue AI session in a different tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Continue current project in Gemini CLI
  python3 continue.py --tool gemini

  # Continue in Codex with more context
  python3 continue.py --tool codex --messages 30

  # Prepare context for Cursor (manual copy)
  python3 continue.py --tool cursor

  # List all sessions for current project
  python3 continue.py --list
        """
    )

    parser.add_argument("--tool", choices=["gemini", "codex", "cursor", "vscode", "copilot"],
                       help="Which AI tool to continue with")
    parser.add_argument("--project",
                       default="/home/dnames/projects/spec-story-local",
                       help="Project path (default: current project)")
    parser.add_argument("--messages", type=int, default=20,
                       help="Number of recent messages to include (default: 20)")
    parser.add_argument("--list", action="store_true",
                       help="List all sessions for this project")
    parser.add_argument("--no-interactive", action="store_true",
                       help="Don't launch tool, just prepare context")

    args = parser.parse_args()

    # Get project sessions
    print(f"\n🔍 Loading sessions for: {args.project}")
    sessions = get_project_sessions(args.project)

    if not sessions:
        print(f"\n❌ No sessions found for project: {args.project}")
        print("\nMake sure ai-history index is up to date:")
        print("  python3 ai-history.py export --all")
        sys.exit(1)

    print(f"✓ Found {len(sessions)} sessions across tools:")

    # Count by tool
    tool_counts = {}
    for s in sessions:
        tool_counts[s.tool] = tool_counts.get(s.tool, 0) + 1

    for tool, count in sorted(tool_counts.items()):
        print(f"  - {tool}: {count} sessions")

    if args.list:
        print(f"\n{'='*60}")
        print("All sessions:")
        print(f"{'='*60}\n")
        for i, session in enumerate(sessions, 1):
            created = session.created_at.strftime('%Y-%m-%d %H:%M') if session.created_at else '???'
            msgs = len(session.messages)
            print(f"{i}. [{session.tool}] {session.title or session.session_id[:12]}")
            print(f"   Created: {created} | Messages: {msgs}")
        return

    if not args.tool:
        print("\n❌ Please specify --tool (gemini, codex, cursor, vscode)")
        print("   Or use --list to see all sessions")
        sys.exit(1)

    # Format context
    print(f"\n📦 Preparing context ({args.messages} recent messages)...\n")
    context = format_context_for_tool(sessions, args.messages)

    # Continue with selected tool
    interactive = not args.no_interactive

    if args.tool == "gemini":
        continue_with_gemini(context, interactive)
    elif args.tool == "codex":
        continue_with_codex(context, interactive)
    elif args.tool == "cursor":
        continue_with_cursor(context)
    elif args.tool in ["vscode", "copilot"]:
        continue_with_vscode(context)

    print("\n✓ Done! You can now continue working in the new tool.")
    print(f"\n💡 All sessions will be tracked in ai-history web UI:")
    print("   http://localhost:5000")

if __name__ == "__main__":
    main()
