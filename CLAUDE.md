# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install
pip install -e . && pre-commit install

# Lint & format (run before committing)
black . --line-length=100
isort . --profile black --line-length=100
flake8 . --max-line-length=100 --ignore=E501,W503,E203
mypy ai_history/ --ignore-missing-imports

# Tests
.venv/bin/python -m pytest tests/                       # all
.venv/bin/python -m pytest tests/test_extractors_contract.py  # single file
.venv/bin/python -m pytest tests/ -k "gemini"           # pattern
.venv/bin/python -m pytest tests/ -v --tb=short         # verbose

# Docker (production stack: app + postgres + redis)
docker compose build app && docker compose up -d app
docker compose logs -f app
docker exec -it ai-history-app bash
```

## Architecture

### Data Flow

```
Tool data dirs  →  Extractor  →  UnifiedSession  →  IndexBuilder  →  ~/.ai-history/index.json
                                                                  →  ~/.ai-history/projects/<id>/session.md
```

`~/.ai-history/` is the persistent output dir (`OUTPUT_DIR` in `web_data.py`). The index is a flat JSON file; SQLite FTS (`search/engine.py`) sits beside it as `index.sqlite`.

### Package Layout

- **`ai_history/core/models.py`** — `UnifiedSession`, `UnifiedMessage`, `Tool` (enum), `Role` (enum). The canonical data model everything else converges to.
- **`ai_history/extractors/`** — One class per AI tool, all inherit `BaseExtractor`. Implement `tool` property + `extract_sessions() -> Iterator[UnifiedSession]` + `is_available()`. Use `safe_copy_db()` from base when reading SQLite files (avoids lock contention).
- **`ai_history/interfaces/web.py`** — Flask app + all routes. Heavy: imports from the 5 sibling modules below.
- **`ai_history/interfaces/web_data.py`** — `load_index()`, `_build_index_from_extractors()`, `OUTPUT_DIR`, `INDEX_PATH`. All index I/O lives here. Uses file-stat-keyed LRU cache (`threadsafe_lru_cache`) — call `clear_index_cache()` after writes.
- **`ai_history/interfaces/web_jobs.py`** — In-memory `RELOAD_JOBS` dict + threading logic for async reload/audit. TTL=3600s, max=256 jobs. Job state: `queued → running → done/error/cancelled`.
- **`ai_history/interfaces/web_utils.py`** — `NOISE_RULES_PATH`, `RATE_LIMIT_STATE`, `METRICS`, `METRICS_LOCK`, rate-limiting, request IDs, metrics counters.
- **`ai_history/interfaces/web_templates.py`** — All HTML/CSS/JS as Python strings (Tailwind + highlight.js, no build step).
- **`ai_history/interfaces/web_services.py`** — Session enrichment, thread building, project payload assembly.

### Entry Points

| Command | File | Notes |
|---|---|---|
| `ai-history` | `ai_history_cli.py` | Full CLI (list, search, export, check…) |
| `ai-session` | `ai_session_cli.py` | Session switching between tools |
| `ai-history-web` | `ai_history_web_new.py` | Thin wrapper → `ai_history.interfaces.web:app` |
| Docker | `Dockerfile` | `gunicorn --workers 1 --threads 8` — must stay at 1 worker; `RELOAD_JOBS` is in-memory |

### Web UI — Reload/Async Jobs

The Sync button (`POST /api/reload-sessions?async=1`) returns a `job_id`; the frontend polls `GET /api/reload-status/<job_id>`. Job state is stored in `RELOAD_JOBS` (in-memory dict in `web_jobs.py`). **Gunicorn must run with `--workers 1`** — multiple workers each have their own dict, causing 404s on status polls.

## Testing Notes

Tests patch symbols via `monkeypatch.setattr`. Because `web.py` re-exports from sub-modules, patch the **origin module**, not `web`:

| Symbol | Patch target |
|---|---|
| `INDEX_PATH`, `DELETED_SESSIONS_PATH`, `load_deleted_session_ids` | `web_data` |
| `NOISE_RULES_PATH` | `web_utils` |
| `ACTION_JOB_TIMEOUT_SECONDS`, `RELOAD_JOB_TTL_SECONDS`, `RELOAD_JOB_MAX` | `web_jobs` |
| `markdown`, `format_message_content` | `web_formatting` |
| `load_index`, `get_all_extractors` | `web` (these are imported into `web` namespace) |

## Code Style

- **100 char line limit**, black + isort enforced via pre-commit
- Type hints on all function signatures
- `Path.expanduser()` / `Path.home()` for all filesystem paths — never hardcode `/home/...`
- stdout for data output, stderr for errors; exit codes 0/1
- `from X import *` is forbidden; explicit imports only
- Bare `except:` is forbidden; catch specific exceptions
