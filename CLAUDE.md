# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Naming

Everything is **Lore**: the product, the CLI binaries (`lore`, `lore-session`,
`lore-web`, `lore-mcp`), the Python import package (`lore`), and the package
directory (`lore/`). The top-level CLI entry modules are `lore_cli.py` and
`lore_session_cli.py`. Config env vars use the `LORE_*` prefix (legacy
`AI_HISTORY_*` names are still read as deprecated aliases — see
`lore/__init__.py:_alias_legacy_env`). The persistent data directory is
`~/.lore` (auto-migrated from the legacy `~/.ai-history` on first run; that
migration path is the only place the old `ai-history` name legitimately survives).

## Commands

```bash
# Install (runtime only)
pip install -e . && pre-commit install
# Install with test/lint/type tooling (pytest, pytest-cov, ruff, mypy, fastembed)
pip install -e ".[dev]"

# Lint & format (run before committing) — ruff replaces black/isort/flake8
ruff format .
ruff check --fix .
mypy lore/ --ignore-missing-imports

# Tests
.venv/bin/python -m pytest tests/                       # all
.venv/bin/python -m pytest tests/test_extractors_contract.py  # single file
.venv/bin/python -m pytest tests/ -k "gemini"           # pattern
.venv/bin/python -m pytest tests/ -v --tb=short         # verbose

# Docker (single service: app — no postgres/redis; SQLite+WAL is the store)
docker compose build app && docker compose up -d app
docker compose logs -f app
docker exec -it lore-app bash   # container name from docker-compose.yml
```

## Architecture

### Data Flow

```
Tool data dirs  →  Extractor  →  UnifiedSession  →  IndexBuilder  →  ~/.lore/index.json
                                                                  →  ~/.lore/projects/<id>/session.md
```

`~/.lore/` is the persistent output dir (`OUTPUT_DIR` in `web_data.py`). The index is a flat JSON file; SQLite FTS (`search/engine.py`) sits beside it as `index.sqlite`.

### Package Layout

- **`lore/core/models.py`** — `UnifiedSession`, `UnifiedMessage`, `Tool` (enum), `Role` (enum). The canonical data model everything else converges to.
- **`lore/extractors/`** — One class per AI tool, all inherit `BaseExtractor`. Implement `tool` property + `extract_sessions() -> Iterator[UnifiedSession]` + `is_available()`. Use `safe_copy_db()` from `utils/paths` when reading SQLite files (avoids lock contention; callers must clean up the temp copy in a `finally`).
- **`lore/interfaces/web.py`** — Flask app + all routes. Heavy: imports from the 5 sibling modules below.
- **`lore/interfaces/web_data.py`** — `load_index()`, `_build_index_from_extractors()`, `OUTPUT_DIR`, `INDEX_PATH`. All index I/O lives here. Uses file-stat-keyed LRU cache (`threadsafe_lru_cache`) — call `clear_index_cache()` after writes.
- **`lore/interfaces/web_jobs.py`** — In-memory `RELOAD_JOBS` dict + threading logic for async reload/audit. TTL=3600s, max=256 jobs. Job state: `queued → running → done/error/cancelled`.
- **`lore/interfaces/web_utils.py`** — `NOISE_RULES_PATH`, `RATE_LIMIT_STATE`, `METRICS`, `METRICS_LOCK`, rate-limiting, request IDs, metrics counters.
- **`lore/interfaces/web_templates.py`** — All HTML/CSS/JS as Python strings (Tailwind + highlight.js, no build step). Tailwind/highlight.js are vendored under `lore/interfaces/static/` and served by Flask (no CDN — offline-safe); re-vendor via `scripts/vendor_assets.py --download`.
- **`lore/interfaces/web_services.py`** — Session enrichment, thread building, project payload assembly.

### Entry Points

| Command | File | Notes |
|---|---|---|
| `lore` | `lore_cli.py` | Full CLI (list, search, export, check…) |
| `lore-session` | `lore_session_cli.py` | Session switching between tools |
| `lore-web` | `lore/cli/web.py` | `main()` → `start_web_ui` (Flask dev server, `--host/--port/--debug`, `LORE_WEB_*` env). Prod = gunicorn `lore.interfaces.web:app` |
| `lore-mcp` | `lore/cli/mcp.py` | `main_sync()` → `create_server().run()` over stdio (Claude Code / OpenCode) |
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

- **100 char line limit**, ruff (format + check) enforced via pre-commit
- Type hints on all function signatures
- `Path.expanduser()` / `Path.home()` for all filesystem paths — never hardcode `/home/...`
- stdout for data output, stderr for errors; exit codes 0/1
- `from X import *` is forbidden; explicit imports only
- Bare `except:` is forbidden; catch specific exceptions
