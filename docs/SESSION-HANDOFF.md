# Session Handoff — 2026-05-06

This document captures the state of the ai-history project at the end of the
2026-05-06 session so a fresh Claude Code session can pick up cold.

## TL;DR

- Public-release prep done; multi-agent review done; Claude sync bug fixed.
- 6 commits on `master` since `38e5ced`.
- 129/129 tests passing.
- Backlog of ~60 items lives in `docs/ROADMAP.md`. Issues NOT yet created.
- Next step: pick a destination (Forgejo or GitHub), run
  `tools/create_issues.sh`, then start work on P0 items.

---

## What we did this session

### 1. Public-release prep (`a530fc9`)

- LICENSE (MIT), SECURITY.md, CONTRIBUTING.md, CLAUDE.md
- `.cursorrules`, `.github/copilot-instructions.md`, `.github/workflows/ci.yml`,
  PR + issue templates
- Removed hardcoded credentials, personal paths, internal URLs
- Externalized `POSTGRES_PASSWORD` via env in `docker-compose.yml`
- Updated `pyproject.toml` with classifiers/keywords/generic author

### 2. Test fixes (`4537c33`)

Fixed 4 pre-existing test failures from template/module drift:
- `reloadBtn`/`auditBtn` → `syncBtn` rename
- Patched `web_formatting.markdown` (origin module) instead of `web.markdown`
- Patched `web_data.INDEX_PATH` (origin module) instead of `web.INDEX_PATH`

### 3. Claude sync bug fix (`d56d69c`)

**Root cause**: dashboard, `/sessions`, render() recents, and project recents
sorted by `created` (file ctime) instead of `updated` (last activity). A
session created 2026-03-24 but still active 2026-05-06 looked stale.

**Fix**: 4 sort sites in `web.py` and `web_services.py` now sort by
`updated` with `created` fallback. Regression test in
`tests/test_session_sort_regression.py`.

### 4. Multi-agent review (`3ccdc0f`)

Six subagents ran in parallel: code-reviewer, security-auditor,
architect-reviewer, performance-engineer, qa-expert, researcher.

Outputs:
- `docs/REVIEW.md` — synthesis of all 6 reports
- `docs/ROADMAP.md` — 60+ backlog items, P0 → P3
- `tools/create_issues.sh` — one-shot issue creator for Forgejo or GitHub

---

## Top 3 release blockers (start here next session)

| # | Title | Severity | File:line |
|---|-------|----------|-----------|
| 1a | docker-compose ships unused Postgres + Redis stack with `changeme` default password; container runs as root | **P0** | `docker-compose.yml`, `Dockerfile:17` |
| 2 | XSS via tool-call rendering — placeholder substitution re-injects HTML AFTER bleach | **P0 critical** | `ai_history/interfaces/web_formatting.py:177-178` |
| 3 | CSRF disabled on every state-changing route | **P0** | `web.py:677,699,726,1110,1250,1265` |

These three plus a handful of related items (#4 path traversal in
`resolve_export_path`, #5 non-root container user, #6 atomic index writes)
should land before any public announcement.

---

## TODO (todos, owners, dependencies)

Numbered IDs match `docs/ROADMAP.md` and the issues that
`tools/create_issues.sh` will create.

### NEXT — must ship before public release

- [ ] **#1a** Drop Postgres + Redis from `docker-compose.yml` and `Dockerfile`. Simplify to single app container. (1h)
- [ ] **#1b** Rename `ai_history_mcp_new.py` → `ai_history.cli.mcp`, `ai_history_web_new.py` → `ai_history.cli.web`. Update `pyproject.toml:42-47`. (1h)
- [ ] **#1c** Atomic `index.json` writes via temp file + `os.replace()`. (`web.py:369`, `web.py:1156`) (30m)
- [ ] **#1d** `safe_copy_db` cleanup of `/tmp/*.vscdb*` via context manager. (`utils/paths.py:64`) (30m)
- [ ] **#1e** Surface extractor exceptions to job result metadata instead of silent `logger.debug`. (`web_data.py:213`, `web.py:870`) (2h)
- [ ] **#1f** MCP server: log exception details server-side, return generic `"Internal error"` to peer. (`interfaces/mcp.py:209`) (30m)
- [ ] **#2** Run `sanitize_rendered_html` over the FINAL composed string after placeholder substitution in `format_message_content`. (`web_formatting.py:177-178`) (2-4h, careful)
- [ ] **#3** Remove `@csrf.exempt` from POST routes. May need API client updates — coordinate with consumers. (4h+)
- [ ] **#4** Enforce `resolved.is_relative_to(OUTPUT_DIR)` in `resolve_export_path`. (`web_data.py:307-324`) (30m)
- [ ] **#5** Dockerfile: `RUN useradd -m -u 10001 ai && USER ai`. Mount under `/home/ai/`. (1h)
- [ ] **#6** Once #1a lands, this is moot. Otherwise remove the `:-changeme` default. (—)

### THEN — security hardening (P1, first month after release)

- [ ] **#7** Replace CSP `'unsafe-inline'` with nonces or hashes. (`web.py:496-497`)
- [ ] **#8** Only honor `X-Forwarded-For` when `TRUSTED_PROXY` env is set. (`web_utils.py:75`)
- [ ] **#9** Refuse to start with ephemeral `SECRET_KEY` when `FLASK_ENV=production`. (`web.py:143`)
- [ ] **#10** Add `pip-audit` job to `.github/workflows/ci.yml`.
- [ ] **#11** Generate `requirements.lock` via `pip-compile` and commit it.
- [ ] **#12** SRI hashes on Tailwind/highlight.js, OR vendor them (see #19).
- [ ] **#13** Drop `data:` from `img-src` CSP.
- [ ] **#14** Already covered by #1a (remove psycopg2-binary, redis from Dockerfile).
- [ ] **#15** Tighten `validate_session_id` to `[A-Za-z0-9_.\-]{1,128}`.
- [ ] **#15a** Plan `bleach` → `nh3` migration (bleach archived 2024).
- [ ] **#15b–c** Add type hints + `from __future__ import annotations` repo-wide.
- [ ] **#15d** Bump `requires-python` to 3.11.
- [ ] **#15e** Pick one toolchain: switch pre-commit from black+isort+flake8 to ruff.

### THEN — performance (P1)

- [ ] **#16** Incremental index sync: per-session mtime check, `INSERT OR REPLACE` only changed rows. **Headline UX win.** (1 day)
- [ ] **#17** Strip `search_text`/`keywords` from dashboard payload. Split `index.json` into `index_meta.json` + `index_search.json`. (1-2h, ~75% size reduction)
- [ ] **#18** FTS5 with `content=sessions` external content table. Halves SQLite size. (4h)
- [ ] **#19** Vendor Tailwind + highlight.js. Drop CDN dep. Restores air-gapped use. (4h)
- [ ] **#20** Streamed indexing for huge sessions (>1k messages). (1 day)

### THEN — architecture / tech debt (P2)

- [ ] **#21** Stop re-exporting from `web.py`; delete `_TEST_EXPORTS`; update tests. Retires the CLAUDE.md monkeypatch table.
- [ ] **#22** Merge `web_helpers.py` into `web_services.py`.
- [ ] **#23** Hoist `_build_search_text`/`_infer_title` out of dual loops in `exporters/index.py`.
- [ ] **#24** Mtime-keyed cache for `load_sessions_for_tool`.
- [ ] **#25** `web_jobs.py` should own `_audit_*` helpers (currently in `web.py`, called via late imports).
- [ ] **#25a** Decompose `session_detail` (199 LOC).
- [ ] **#25b** Decompose `mcp.create_server()` (445 LOC).
- [ ] **#25c** Move HTML out of `web_templates.py` (2,036 LOC) to `ai_history/templates/*.html`.
- [ ] **#25d** Build Jinja2 `Environment` once at module import.
- [ ] **#25e** `BaseExtractor.iter_sqlite_dbs()` helper.
- [ ] **#25f** Centralize tool data root paths in `utils/paths`.

### THEN — QA (P1–P2)

- [ ] **#26** Parametrized contract test across all 11 extractors.
- [ ] **#27** Tests for antigravity/copilot/cursor/vscode (currently zero coverage).
- [ ] **#28** Public `/api/v1/*` route contract tests.
- [ ] **#29** `pytest-cov` + 80% coverage gate.
- [ ] **#30** Smoke test: boot Flask, hit `/api/health`, `/api/ready`, `/api/build-info`.
- [ ] **#31** Schema snapshot test for `index.json`.
- [ ] **#32** Property-based parser tests (`hypothesis`) feeding malformed JSONL.
- [ ] **#33** `pytest-randomly`.

### LATER — features (P1–P2, post-release driven by user feedback)

- [ ] **#34** Token cost dashboard. (1 week, **headline feature**)
- [ ] **#35** Semantic search (sqlite-vec + nomic-embed-text via Ollama). **Nobody else has this.**
- [ ] **#36** Shareable static HTML export.
- [ ] **#37** Polished `ai-history rules` UI; lead the README with it. (SpecStory's hook)
- [ ] **#38** Session timeline / git-diff view.
- [ ] **#39** Project-level cost attribution.
- [ ] **#40** Noise filter web UI.
- [ ] **#41** MCP-over-HTTP transport.
- [ ] **#42** Verify and deepen Warp Block import.
- [ ] **#43** `ai-history digest` weekly summary.

### LATER — v3 redesign (P3)

- [ ] **#44** Single SQLite source of truth (drop `index.json`).
- [ ] **#45** Persistent JobStore (multi-worker safe). Unblocks gunicorn `--workers >1`.
- [ ] **#46** Jinja templates on disk + Tailwind CLI prebuild.
- [ ] **#47** Optional FastAPI alongside Flask.
- [ ] **#48** Plugin extractor SDK.

### LATER — marketing (P2)

- [ ] **#49** Reposition README around "your AI sessions ARE documentation".
- [ ] **#50** Comparison table vs claude-code-history-viewer / claude-history / specstory.

---

## Decision pending: where do issues go?

Two options ready in `tools/create_issues.sh`:

1. **Forgejo** at `git.erdlabs.com` / `100.119.46.15:3000` (Tailscale-only).
   The repo `erdna/ai-history` already exists. From a Tailscale-connected
   machine: `tools/create_issues.sh forgejo`. The previous Claude session
   could not reach the host (no Tailscale on the runner network).

2. **GitHub** — no public repo exists yet. To create one:
   `gh repo create <owner>/ai-history --public --source=. --remote=github --push`
   then `tools/create_issues.sh github <owner> ai-history`.

The script:
- Creates 13 labels with colors (p0/p1/p2/p3, bug, security, enhancement,
  performance, architecture, docs, tech-debt, extractor, qa)
- Posts ~50 issues with proper labels, titles prefixed with the roadmap ID,
  body referencing exact file:line locations.

---

## Files of interest for the next session

| Path | Purpose |
|------|---------|
| `docs/ROADMAP.md` | full prioritized backlog (60+ items) |
| `docs/REVIEW.md` | synthesis of multi-agent findings |
| `tools/create_issues.sh` | bulk issue creator |
| `CLAUDE.md` | architecture + commands + monkeypatch table |
| `tests/test_session_sort_regression.py` | regression for the bug fixed today |
| `ai_history/interfaces/web.py` | 1,300 LOC, the route layer |
| `ai_history/interfaces/web_formatting.py:177` | XSS hot spot (#2) |
| `ai_history/interfaces/web_data.py:307` | path traversal hot spot (#4) |
| `ai_history/extractors/claude.py` | reviewed clean, no issues |

---

## Session memory hints

- User language: German preferred for casual chat; technical/code in English.
- User role: tech lead / hobbyist building this for personal multi-tool
  AI session aggregation. Has pivoted multiple times across agents/models;
  expects the project history to be messy and explicitly asked for
  cleanup.
- Forgejo (Tailscale-only) is the user's private git host; GitHub is for
  public OSS repos.
- Test runner: `.venv/bin/python -m pytest tests/`. Currently 129/129.
- `~/.ai-history/` is the canonical output dir — do not relocate.
- The user's index has 1672 sessions. Largest single session: 15K messages.

## Next-session opening prompt suggestion

> Read docs/SESSION-HANDOFF.md and pick up from there. We landed the
> Claude sync fix and the multi-agent review last session. Decide where
> to publish issues (Forgejo or new GitHub repo), run
> tools/create_issues.sh, then start on P0 items #1a (drop Postgres
> stack) and #2 (XSS sanitization).
