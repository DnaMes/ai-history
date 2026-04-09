# GEMINI.md - Project Instructional Context

## Project Overview
**ai-history** is a local-first, privacy-focused AI chat history manager and session switcher. It consolidates chat histories from various AI coding assistants into a unified local database/index and provides a modern web interface for browsing and searching conversations.

### Key Features
- **Unified Extraction**: Supports Claude Code, Cursor, Gemini CLI, Codex, VSCode Copilot, Warp, and GitHub Copilot CLI.
- **Seamless Context Switching**: Transition sessions between tools (e.g., Claude -> Gemini) with pre-loaded context.
- **Modern Web Dashboard**: A SpecStory-inspired UI with dark mode, collapsible tool outputs, and syntax highlighting.
- **MCP Integration**: Exposes history management as tools for AI assistants like Claude.
- **Local-First Architecture**: No cloud connectivity required; data stays on the machine.

### Architecture & Tech Stack
- **Backend**: Python 3.11+ (Modular package structure under `ai_history/`).
- **Web Interface**: Flask with Jinja2 templates, Tailwind CSS, and highlight.js.
- **Data Model**: Unified session and message objects (`ai_history/core/models.py`).
- **Database**: Hybrid approach using `index.json` for rapid indexing and PostgreSQL for persistent storage.
- **Infrastructure**: Dockerized environment with Postgres and Redis.

---

## Building and Running

### Prerequisites
- Python 3.9+
- Docker and Docker Compose (for the full stack)
- Required Python packages: `flask`, `markdown`, `psycopg2-binary`, `redis`

### Installation
```bash
# Clone the repository
git clone <repo-url>
cd ai-history

# Install in editable mode
pip install -e .
```

### Key Commands
- **Check Environment**: `python3 ai_history_cli.py check` (Verifies available AI tool configurations).
- **List Sessions**: `python3 ai_history_cli.py list --since 7d` (Shows recent activity).
- **Start Web UI (Local)**: `python3 ai_history_web_new.py` (Runs Flask dev server).
- **Start Full Stack (Docker)**: `./start_stack.sh` (Launches App + Postgres + Redis).
- **Switch Tools**: `python3 ai_session_cli.py switch gemini` (Transfers context to Gemini CLI).

---

## Development Conventions

### Package Structure
- `ai_history/core`: Domain models and business logic.
- `ai_history/extractors`: Logic for parsing specific AI tool databases/logs.
- `ai_history/utils`: Shared utilities for path detection, datetime parsing, and text processing.
- `ai_history/interfaces`: Entry points for CLI, Web, and MCP.
- `ai_history/exporters`: Formatters for Markdown and Context files.

### Coding Style
- **Modular Extractors**: Each tool has its own extractor class inheriting from `BaseExtractor`.
- **Safe DB Access**: Use `safe_copy_db` utility when reading SQLite files to avoid locking issues.
- **Regex Formatting**: Use non-greedy regex patterns for parsing tool outputs to ensure clean UI rendering.
- **UI Design**: Adhere to "Apple-like" minimalism (Zinc/Dark palette, Document-flow layout).

### Implementation Details to Note
- **Warp Extraction**: Focuses on user prompts as responses are often stored remotely.
- **Cursor Extraction**: Uses deep scanning of `fullConversationHeadersOnly` and linked `bubbleId` blobs for complete history.
- **Context Preparation**: The `ai-session` tool generates a temporary Markdown file (`/tmp/ai-session-context.md`) to pass history between tools.
