# GEMINI.md - Project Instructional Context

## Project Overview
**Lore** is a local-first, privacy-focused tool that is both an **archive** of
AI coding sessions and a **shared agent memory**. It consolidates chat histories
from various AI coding assistants into a unified local database/index, provides
a modern web interface for browsing and searching conversations, and exposes a
cross-tool knowledge store that agents write to and recall from.

> Product/CLI = **Lore** (`lore`, `lore-session`, `lore-web`, `lore-mcp`).
> The Python import package is `lore` — deliberately not renamed.

### Key Features
- **Unified Extraction**: Supports Claude Code, Cursor, Gemini CLI, Codex, VSCode Copilot, Warp, and GitHub Copilot CLI.
- **Shared Agent Memory**: A cross-tool knowledge store (facts, decisions, lessons) with keyword + semantic search and provenance.
- **Seamless Context Switching**: Transition sessions between tools (e.g., Claude -> Gemini) with pre-loaded context.
- **Modern Web Dashboard**: A SpecStory-inspired UI with dark mode, collapsible tool outputs, and syntax highlighting.
- **MCP Integration**: Exposes history and shared memory as tools for AI assistants like Claude.
- **Local-First Architecture**: No cloud connectivity required; data stays on the machine.

### Architecture & Tech Stack
- **Backend**: Python 3.11+ (Modular package structure under `lore/`).
- **Web Interface**: Flask with Jinja2 templates, Tailwind CSS, and highlight.js.
- **Data Model**: Unified session and message objects (`lore/core/models.py`).
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
git clone https://github.com/DnaMes/lore.git
cd lore

# Install in editable mode
pip install -e .
```

### Key Commands
- **Check Environment**: `lore check` (Verifies available AI tool configurations).
- **List Sessions**: `lore list --since 7d` (Shows recent activity).
- **Start Web UI (Local)**: `lore-web` (Runs Flask dev server).
- **Start Full Stack (Docker)**: `./start_stack.sh` (Launches App + Postgres + Redis).
- **Switch Tools**: `lore-session switch gemini` (Transfers context to Gemini CLI).

(The underlying entry modules are `lore_cli.py`, `lore_session_cli.py`, and
`lore/cli/web.py`; the installed CLI binaries are the `lore*` commands.)

---

## Development Conventions

### Package Structure
- `lore/core`: Domain models and business logic.
- `lore/extractors`: Logic for parsing specific AI tool databases/logs.
- `lore/utils`: Shared utilities for path detection, datetime parsing, and text processing.
- `lore/interfaces`: Entry points for CLI, Web, and MCP.
- `lore/exporters`: Formatters for Markdown and Context files.

### Coding Style
- **Modular Extractors**: Each tool has its own extractor class inheriting from `BaseExtractor`.
- **Safe DB Access**: Use `safe_copy_db` utility when reading SQLite files to avoid locking issues.
- **Regex Formatting**: Use non-greedy regex patterns for parsing tool outputs to ensure clean UI rendering.
- **UI Design**: Adhere to "Apple-like" minimalism (Zinc/Dark palette, Document-flow layout).

### Implementation Details to Note
- **Warp Extraction**: Focuses on user prompts as responses are often stored remotely.
- **Cursor Extraction**: Uses deep scanning of `fullConversationHeadersOnly` and linked `bubbleId` blobs for complete history.
- **Context Preparation**: The `ai-session` tool generates a temporary Markdown file (`/tmp/ai-session-context.md`) to pass history between tools.
