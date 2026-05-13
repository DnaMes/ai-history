# HANDOFF — ai-history — 2026-05-13

> Claude: update this before session ends with /compact or on Stop.

## Current Task

Project finalization for public release — all P0 and P1 issues resolved, 10 P2/P3 issues remain.

## Decisions Made

- CSP nonces: `secrets.token_urlsafe(16)` per-request, stored in `flask.g.csp_nonce`; all 8 inline script/style tags updated
- Coverage gate: 80% via `[tool.coverage.*]` in pyproject.toml; excluded LLM/watcher/SQLite-only extractors from coverage
- API contract tests use `app.test_client()` with mocked `load_index` — no disk needed
- `project_label` and `parse_date_param` now accept `Optional[str]` (was `str`) — matches how they're called from tests

## Files Changed This Session

| File | Change |
|------|--------|
| `ai_history/interfaces/web.py` | CSP nonces via before_request, ProxyFix, SECRET_KEY warning, incremental reload, resume endpoint, stats endpoint |
| `ai_history/interfaces/web_templates.py` | nonce="{{ nonce }}" on all inline script/style tags; STATS_TEMPLATE added |
| `ai_history/interfaces/web_helpers.py` | Optional[str] on project_label/parse_date_param |
| `ai_history/interfaces/web_data.py` | threadsafe_lru_cache types, incremental index build |
| `ai_history/watcher.py` | new SessionWatcher class |
| `ai_history/utils/git.py` | new get_git_info() |
| `ai_history/exporters/markdown.py` | mtime-based skip, atomic writes, git_commit frontmatter |
| `ai_history/exporters/index.py` | incremental reuse, _stat_mtime_ns exported |
| `pyproject.toml` | [tool.pyright], [tool.coverage.*], [tool.pytest.ini_options] with addopts |
| `.github/workflows/tests.yml` | --cov-fail-under=80 added |
| `README.md` | CI badges, ASCII mockup, fixed clone URL, Python 3.11+ |
| `tests/test_api_contract.py` | 25 API route contract tests |
| `tests/test_extractor_contracts.py` | 101 parametrized extractor interface tests |
| `tests/test_csp_nonces.py` | 13 CSP nonce tests |
| `tests/test_*.py` (12 new) | coverage tests for extractors, utils, web layer |

## Current State

- **Tests**: 656 passing, 80.33% coverage
- **GitHub issues**: 10 open (down from 32), all P0 closed, all P1 closed except #17 (split index.json) and #19 (vendor Tailwind)
- **Both remotes in sync**: `github` and `forgejo` both at `7cea447`

## Open Issues (10 remaining)

| # | Label | Issue |
|---|-------|-------|
| 32 | p3 | Single SQLite source of truth (v3 milestone) |
| 31 | p2 | Decompose mcp.create_server() — 445 LOC |
| 30 | p2 | Move HTML to Jinja2 templates |
| 29 | p2 | MCP-over-HTTP transport |
| 28 | p2 | Shareable static HTML export |
| 27 | p2 | ai-history digest command |
| 24 | p2 | Scoped MCP search |
| 22 | p2 | Aider extractor |
| 16 | p1 | Vendor Tailwind CSS + highlight.js |
| 15 | p1 | Split index.json (19 MB payload) |

## Next Steps (recommended order)

1. **#17 / issue 15** — Split index.json: paginated API already exists (`/api/v1/sessions?page=N`), need frontend to use it instead of loading all at once
2. **#19 / issue 16** — Vendor Tailwind + highlight.js: `npm run build` → single CSS bundle, no CDN needed
3. **#51 / issue 22** — Aider extractor: reads `~/.aider/` chat logs (JSON/markdown format)
4. **#43 / issue 27** — Digest command: `ai-history digest --since 7d` → LLM summary of what was built
