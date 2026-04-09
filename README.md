# ai-history 📚

**The Local-First AI Chat History Manager.**

A professional, privacy-focused alternative to SpecStory that collects, unifies, and exports chat histories from all your AI coding assistants without any cloud connectivity.

![Version](https://img.shields.io/badge/version-2.0.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)

---

## 🎯 Features

- **Unified History**: See all chats from Claude Code, Cursor, Gemini CLI, Codex, VSCode Copilot, Warp, and more in one place.
- **Smart Context Switching**: Seamlessly move a session from one tool to another (e.g., Claude -> Gemini) when hitting rate limits.
- **Modern Web Dashboard**: A polished, SpecStory-inspired UI with Markdown rendering, code highlighting, and full-text search.
- **MCP Integration**: Control your history and tool-switching directly from within Claude Code.
- **Privacy First**: Everything stays local on your machine. No cloud, no tracking.

---

## 🚀 Quick Start

### Installation

```bash
git clone https://github.com/dnames/ai-history.git
cd ai-history
pip install -e .
```

If you see `ModuleNotFoundError: ai_history_cli`, rerun `pip install -e .` to refresh entry points.

### Basic Commands

```bash
# Check available AI tools on your system
ai-history check

# List recent sessions
ai-history list --since 7d

# Search across all sessions
ai-history search "database migration"

# Start the Web UI
ai-history-web

# Run a tool and sync its session after exit
ai-history run codex

# Sync existing sessions for a tool
ai-history sync gemini

# List threads for cross-tool continuation
ai-history threads

# Generate derived rules (SpecStory-style)
ai-history rules --limit 30
```

---

## 🔄 Session Management (The Switcher)

The `ai-session` tool allows you to jump between tools with full context.

### Scenario: Claude Code Rate Limit Reached

1. You are in Claude and see "Usage Limit Reached".
2. Run: `ai-session switch gemini`
3. Gemini CLI starts with the last 15 messages from your Claude session pre-loaded as context.

```bash
# Manual switch
ai-session switch <tool> [--messages N]

# Continue a specific thread
ai-session switch <tool> --thread-id <thread-id>

# Auto-select best tool
ai-session continue
```

## 🧰 SpecStory-Style Workflow

`ai-history` supports a SpecStory-like flow:

```bash
# Wrap a tool session, then sync after it ends
ai-history run claude

# Backfill/sync existing sessions for a tool
ai-history sync codex
```

`ai-history run` writes a PTY log to `~/.ai-history/runs/` for audit/debugging.

---

## 🔌 MCP Server Setup

Enable `ai-history` tools within Claude Code by adding this to your `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "ai-history": {
      "command": "python3",
      "args": ["/absolute/path/to/ai-history-mcp.py"]
    }
  }
}
```

### Tools provided:

- `search_history`: Find past solutions across all tools.
- `list_sessions`: See what you worked on.
- `switch_to_tool`: Ask Claude to move the session to Gemini for you!

---

## 🎨 Web UI

Browse your history at `http://localhost:5000`.

- **Dashboard**: High-level stats and recent activity.
- **Search**: `Cmd+K` global search with SQLite FTS.
- **Chat View**: SpecStory-style session layout with left TOC.
- **Threads**: Cross-tool continuity view of a project thread.
- **Rules**: Derived rules extracted from assistant responses.
- **Export**: Save any session as a clean Markdown file.

### Security Probe Matrix

Run deterministic route/API hardening probes against a local or deployed web URL:

```bash
# Local
ai-history-web-probe --base-url http://127.0.0.1:5000

# Deployed target protected by Basic auth
export AI_HISTORY_WEB_PROBE_PASSWORD='your-password'
ai-history-web-probe \
  --base-url https://ai-sessions.local.erdlabs.com \
  --user admin \
  --password-env AI_HISTORY_WEB_PROBE_PASSWORD


# Increase timeout/retries when remote index fallback is slow
ai-history-web-probe --base-url https://ai-sessions.local.erdlabs.com --user admin \
  --password-env AI_HISTORY_WEB_PROBE_PASSWORD --timeout-seconds 30 --timeout-retries 2
```

Probe output now includes a `build_info` object fetched from `/api/build-info` (status,
revision, module) so deployed/runtime drift can be diagnosed quickly during parity checks.
Query-parameter hardening probes use URL-encoded metacharacters (for example `%3B`) so
gateway/proxy normalization does not mask application-level validation behavior.

You can query it directly:

```bash
curl -u admin:"$AI_HISTORY_WEB_PROBE_PASSWORD" \
  https://ai-sessions.local.erdlabs.com/api/build-info
```

Note: `/export/<session_id>` first serves linked markdown from `index.json`. If the session
is indexed but the markdown file is missing, it now regenerates markdown from the live
session for that tool. For unknown session ids, it returns `404` directly to avoid
expensive scans unless you explicitly set `AI_HISTORY_EXPORT_FALLBACK_SCAN=true`.

Exit codes:

- `0`: all probes passed
- `1`: probe failures
- `3`: blocked by upstream gateway auth (for example Traefik `401`)

---

## 🏗️ Architecture

- `ai_history/core`: Data models and unified session logic.
- `ai_history/extractors`: Tool-specific logic for parsing histories.
- `ai_history/exporters`: Markdown and Context formatting.
- `ai_history/interfaces`: CLI, Web, and MCP entry points.

---

## 🛠️ Requirements

- Python 3.9+
- Flask (for Web UI)
- Markdown (for rendering)
- highlight.js (included via CDN)
- Tailwind CSS (included via CDN)

## ⚙️ Gemini Project Resolution

If Gemini CLI projects don't map back to a path on your machine, set:

```bash
export GEMINI_PROJECT_ROOTS="$HOME/projects:$HOME/work:$HOME/code"
```

This helps `ai-history` resolve Gemini's project hash to real folders.

---

## 📜 License

MIT License. Built for developers who value their context.

## Production Ops

The web interface now includes built-in hardening and operational endpoints for deployment checks and monitoring.

### Health, readiness, and metrics

```bash
# Liveness (process up + revision)
curl http://127.0.0.1:5000/api/health

# Readiness (filesystem/index checks)
curl -i http://127.0.0.1:5000/api/ready

# JSON metrics counters
curl http://127.0.0.1:5000/api/metrics

# Prometheus text format
curl http://127.0.0.1:5000/api/metrics?format=prom
```

### Request tracing and headers

- Every response includes `X-Request-ID` for correlation.
- API responses include `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset`.
- Security headers include stricter CSP, `X-Frame-Options`, and `Referrer-Policy`.

### Rate limiting configuration

```bash
# Master switch
export AI_HISTORY_RATE_LIMIT_ENABLED=true

# Shared window in seconds
export AI_HISTORY_RATE_LIMIT_WINDOW_SECONDS=60

# Per-endpoint budgets per window
export AI_HISTORY_RATE_LIMIT_MAX_API_REQUESTS=240
export AI_HISTORY_RATE_LIMIT_SEARCH_PER_WINDOW=180
export AI_HISTORY_RATE_LIMIT_AUDIT_PER_WINDOW=20
export AI_HISTORY_RATE_LIMIT_RELOAD_PER_WINDOW=12
```

### Logging mode

```bash
# Optional JSON request logs for easier ingestion
export AI_HISTORY_JSON_REQUEST_LOGS=true
```

When enabled, API/error requests are logged as JSON objects with method, path, status, duration, and request id.

### Docker Compose production defaults

Container runtime uses Gunicorn (`ai_history_web_new:app`) instead of Flask development server.

`docker-compose.yml` now includes health checks for `app`, `db`, and `redis`, and startup ordering waits for healthy dependencies.

```bash
# Validate compose config
docker compose config

# Start stack in background
docker compose up -d

# Watch health state
docker compose ps
```

Example `.env` values for deployment:

```bash
AI_HISTORY_RATE_LIMIT_ENABLED=true
AI_HISTORY_RATE_LIMIT_WINDOW_SECONDS=60
AI_HISTORY_RATE_LIMIT_MAX_API_REQUESTS=240
AI_HISTORY_RATE_LIMIT_SEARCH_PER_WINDOW=180
AI_HISTORY_RATE_LIMIT_AUDIT_PER_WINDOW=20
AI_HISTORY_RATE_LIMIT_RELOAD_PER_WINDOW=12
AI_HISTORY_JSON_REQUEST_LOGS=false
```

