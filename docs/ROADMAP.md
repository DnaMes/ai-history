# ai-history — Product Roadmap

Date: 2026-05-06
Source: synthesis of multi-agent review (security, architecture, performance, QA, competitive research) + user-reported Claude sync bug.

---

## Now (P0 — fixed or imminent, weeks)

### Bugs

- **#1 Claude Code sessions appeared stale** — FIXED in `d56d69c`. Dashboard, `/sessions`, `/sessions?tool=claude` and project recents now sort by `updated` (last activity) with fallback to `created`. Long-running sessions (created weeks ago, still active) now surface at the top.
- **#1a docker-compose ships a Postgres + Redis stack the code does not use** — `docker-compose.yml` exports `DATABASE_URL`/`REDIS_URL` and `Dockerfile` installs `psycopg2-binary` and `redis`, but the codebase stores everything in JSON+SQLite. Public-release blocker; contradicts the "local-first" claim in README/CLAUDE.md. **Action**: delete the db/redis services and the unused deps, simplify compose to just the app container.
- **#1b `_new` suffixes on entry-point modules** — `ai_history_mcp_new.py` and `ai_history_web_new.py` are root-level legacy artifacts referenced by `pyproject.toml:42-47`. Embarrassing on PyPI. Move into the package as `ai_history.cli.mcp` / `ai_history.cli.web`.
- **#1c Index writes are non-atomic** — `web.py:369` and `web.py:1156` open `INDEX_PATH` `"w"` then `json.dump`. SIGINT mid-write corrupts the index for every session. Use `tempfile.NamedTemporaryFile` + `os.replace`.
- **#1d `safe_copy_db` leaks temp DB copies forever** — `utils/paths.py:64-92`. Every reload leaves `*.vscdb`, `*.sqlite`, plus `-wal`/`-shm` in `/tmp`. Add `try/finally` cleanup or context manager.
- **#1e Extractor exceptions silently swallowed at `logger.debug`** — `web_data.py:213-217`, `web.py:870-873`. A failing extractor disappears with zero user-visible signal. Surface to job result metadata.
- **#1f MCP server returns exception details in wire response** — `interfaces/mcp.py:209-211` catches bare `Exception` and embeds it. Leaks stack traces and file paths to peer. Log server-side, return generic `"Internal error"`.
- **#2 Tool-call args bypass HTML sanitization (XSS)** — `web_formatting.py:177-178` re-injects unsanitized HTML AFTER `bleach.clean`. Run `sanitize_rendered_html` over the FINAL composed string. **Severity: critical for any deployment beyond `127.0.0.1`.**
- **#3 CSRF disabled on every state-changing API route** — `@csrf.exempt` on POSTs `/api/reload-sessions`, `/api/cache/clear`, `/session/<id>/delete`, `/api/noise-rules`. Behind a reverse proxy with cookies, a malicious page can trigger destructive actions. Remove `@csrf.exempt` or require `X-Requested-With`.
- **#4 Path traversal via poisoned `export_path`** — `resolve_export_path` does not enforce containment under `OUTPUT_DIR`. If `~/.ai-history/index.json` is shared/tampered, `GET /export/<id>` could read arbitrary files. Add `resolved.is_relative_to(OUTPUT_DIR)`.
- **#5 Container runs as root** — `Dockerfile` has no `USER` directive; bind-mounts read-only host secrets into `/root/`. Add non-root user.
- **#6 Default Postgres password fallback `changeme`** — `docker-compose.yml` resolves `${POSTGRES_PASSWORD:-changeme}` to a known weak default. Remove the default; fail fast.

### Security hardening (P0–P1)

- **#7 CSP `'unsafe-inline'` for scripts/styles** — replace with nonces or hashes (inline scripts are static).
- **#8 X-Forwarded-For trusted without proxy validation** — IP spoofing bypasses rate limiter; only honor when `TRUSTED_PROXY` env is set.
- **#9 SECRET_KEY ephemeral in production** — log a warning if `FLASK_SECRET_KEY` is unset; refuse to start when `FLASK_ENV=production`.
- **#10 Missing dependency CVE scanning in CI** — add `pip-audit` job.
- **#11 Pin transitive dependencies** — generate `requirements.lock` (e.g. via `pip-compile`).
- **#12 Add SRI to CDN script tags** — Tailwind/highlight.js loaded without `integrity=`. Pin versions and add hashes, or self-host (see #18).
- **#13 Drop `data:` from `img-src` CSP** — combined with #2 enables SVG-based payloads.
- **#14 Remove dead Docker deps `psycopg2-binary` and `redis`** — installed but unused; expand attack surface.
- **#15 `validate_session_id` is too permissive** — allows `:`, `*`, `?`, spaces. Tighten to `[A-Za-z0-9_.\-]{1,128}`.
- **#15a `bleach` is archived upstream (2024)** — `pyproject.toml:32`. Plan migration to `nh3` (Rust port), or pin a known-good version with a documented EOL.
- **#15b Type hint coverage ~50%** — 69/136 functions in `web.py`/`web_data.py`/`mcp.py`/`opencode.py`/`warp.py` lack annotations. Global rule says "required on all function signatures".
- **#15c Only 1 of 49 modules uses `from __future__ import annotations`** — adopt repo-wide.
- **#15d `requires-python = ">=3.9"` contradicts CLAUDE.md ("3.11+") and `dict[str, ...]` syntax used throughout** — bump floor to 3.11.
- **#15e Pre-commit uses black+isort+flake8 but global rules say `ruff`** — pick one toolchain (recommend `ruff format` + `ruff check`).

---

## Next (P1 — first month)

### Performance

- **#16 Incremental index sync** — currently every Sync rebuilds the full index from scratch (DELETE + bulk INSERT 1672 rows; full re-parse of every JSONL). Add per-session mtime check; only re-parse changed files. Expected: O(changed) instead of O(all). Headline UX improvement.
- **#17 Strip `search_text`/`keywords` from dashboard payload** — `load_index()` returns 19 MB containing fields the dashboard never reads. Split into `index_meta.json` (cards) and `index_search.json` (only on `/search`). Expected: ~75% reduction in payload + parse cost.
- **#18 FTS5 with `content=sessions` external content table** — eliminates the `search_text` duplication between `sessions` and `sessions_fts`. Halves SQLite size (~40 MB reclaim) and speeds cold cache.
- **#19 Vendor Tailwind + highlight.js** — drop CDN dependency, ship `static/app.css`. Removes #12 + restores air-gapped/offline use as documented in `AGENTS.md:149`.
- **#20 Streamed indexing for huge sessions** — `IndexBuilder` only uses `messages[:30]` + `messages[:20]` for indexing; `claude.py` accumulates all 15 K messages in RAM. Add a short-circuit indexing path that yields metadata + first N messages without materializing the rest.

### Architecture

- **#21 Stop re-exporting from `web.py`** — the `_TEST_EXPORTS` shim and CLAUDE.md monkeypatch table both hint at the same issue: leaky modularization. Delete the re-exports, fix the ~6 dependent tests, retire the patch table.
- **#22 Move `web_helpers.py` into `web_services.py`** — six sibling modules is one too many; merge to five.
- **#23 Hoist `_build_search_text`/`_infer_title` out of dual loops** — currently runs twice (once for JSON, once for SQLite).
- **#24 Mtime-keyed cache for `load_sessions_for_tool`** — currently invalidated only on process restart. Mirror the `_load_index_cached` pattern.
- **#25 Inversion: `web_jobs.py` should own `_audit_*` helpers** — currently `web.py` defines them and `web_jobs.py` reaches back via late imports.
- **#25a Split `session_detail` (199 LOC, cyclomatic ~25)** — `web.py:908-1106` mixes controller + 5 nested closures + an OpenCode-specific fallback. Decompose into controller + renderer.
- **#25b Split `mcp.create_server()` (445 LOC)** — `interfaces/mcp.py:214` defines every tool inline. Move each tool to its own function or sub-module.
- **#25c Move HTML out of `web_templates.py`** — 2,036 LOC of HTML/JS/CSS in Python strings. The `template_folder=` arg in `web.py:142` is set but unused. Move to `ai_history/templates/*.html` and load via `FileSystemLoader`. Enables editor syntax highlighting + a11y linting.
- **#25d Build Jinja2 `Environment` once at module import** — `web.py:412-418` creates a new env on every `render()` call, defeating template caching.
- **#25e Common SQLite-DB iteration helper in `BaseExtractor`** — pattern `is_available → for db in db_paths → safe_copy → connect ro → try/except` repeated nearly verbatim in `warp.py`, `cursor.py`, `vscode.py`, `opencode.py`. Hoist to `BaseExtractor.iter_sqlite_dbs()`.
- **#25f Centralize tool data root paths** — `Path.home() / ".cursor" / ...` etc. repeated ~25 times. Move to `utils/paths.tool_data_root("opencode")`.

### QA / CI

- **#26 Parametrized contract test across all 11 extractors** — `@pytest.mark.parametrize("extractor_cls", ALL_EXTRACTORS)` asserting `Tool`/`Role` enums, `is_available()`, iterator type. Today: only Claude/Gemini/Codex are checked.
- **#27 Add tests for antigravity/copilot/cursor/vscode extractors** — currently zero coverage.
- **#28 Public `/api/v1/*` route contract tests** — locks the OSS API surface before users depend on it.
- **#29 Add `pytest-cov` + 80% coverage gate** — publish HTML artifact.
- **#30 Smoke test booting Flask + hitting `/api/health`, `/api/ready`, `/api/build-info`** — catches deployment regressions.
- **#31 Schema snapshot test for `index.json`** — golden file to catch silent format breaks.
- **#32 Property-based parser tests (hypothesis)** — feed malformed JSONL to each `_parse_session*`; must not raise uncaught.
- **#33 `pytest-randomly`** — expose order-dependence in tests touching `~/.ai-history/`.

---

## Soon (P2 — first quarter)

### Features (from competitive research)

- **#34 Token cost dashboard** — per tool / project / over time. Headline missing feature; claude-code-history-viewer ships it. ~1 week effort, high impact.
- **#35 Semantic search via local embeddings** — `sqlite-vec` + `nomic-embed-text` via Ollama. Zero competitors have shipped this. "Find sessions where I debugged auth middleware" — queries FTS misses.
- **#36 Shareable static HTML export** — single self-contained file per session, zero deps, works via email/file share. SpecStory does this with cloud links — we can do it offline-first.
- **#37 Auto-generate `.cursorrules` / `CLAUDE.md` from history** — `ai-history rules` already exists; promote to headline feature, polish output, expose in web UI.
- **#38 Session timeline / git-diff view** — show file changes alongside conversation. Massive value for code review and audit; nobody has shipped this.
- **#39 Project-level cost attribution** — pairs with #34; lets developers bill clients or justify AI spend.
- **#40 Noise filter UI** — `NOISE_RULES_PATH` exists; expose as drag-and-drop web UI with live preview.
- **#41 MCP-over-HTTP server mode** — `ai_history_mcp_new.py` is local stdio; add `--transport streamable-http` so Cursor and other MCP hosts can query history.
- **#42 Warp Block deeper import** — verify Warp coverage matches spec; add block-level extraction.
- **#43 `ai-history digest` command** — weekly summary report (sessions, cost, top projects). Habit-forming; trivial to ship.

---

## Later (P3 — strategic, v3 redesign)

- **#44 Single SQLite source of truth** — drop `index.json`; sessions/stats live only in SQLite. Eliminates the JSON↔SQLite double write hot path.
- **#45 Persistent JobStore (multi-worker safe)** — `RELOAD_JOBS` in-memory dict forces gunicorn `--workers 1`. Add `SQLiteJobStore` (default) and `RedisJobStore` (opt-in; Redis is already in compose).
- **#46 Templates → Jinja files on disk + Tailwind CLI prebuild** — `web_templates.py` (2,036 LOC of stringly-typed HTML/CSS/JS) was a smart shortcut at 200 LOC, negative at 2,000.
- **#47 Optional FastAPI alongside Flask** — reuse the services layer, expose typed OpenAPI for the public v1 API.
- **#48 Plugin extractor SDK** — `pip install ai-history-extractor-foo` style. Pre-stable plugin API + cookiecutter template.

---

## Marketing / positioning

- **#49 Lead README with "your AI sessions ARE documentation"** — SpecStory's framing. ai-history already generates rules; the gap is positioning, not code.
- **#50 Compare-against table in README** — claude-code-history-viewer (1.2 k stars), claude-history (244), claude-run (592). Highlight the multi-tool moat.

---

## Triage notes

- Items #1–#15 should ship before the public release announcement.
- Items #16–#33 are the v2.1 / v2.2 milestones (within ~30 days of release).
- Items #34+ are post-launch features driven by user feedback. Don't pre-build all of them.
- v3 redesign (#44–#48) only happens once the user count justifies the rework. Until then, the current architecture is fine for `<10 K` sessions.
