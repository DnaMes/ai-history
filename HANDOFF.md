# HANDOFF — ai-history — 2026-05-17

> Claude: update this before session ends with /compact or on Stop.

## Current Task

Project finalization for public release — **all P0/P1 closed**; working
through optional P2/P3 enhancements. Aider extractor (#51) done this session.
7 P2/P3 issues remain, none release-blocking.

## ⚠️ Forgejo out of sync

The Forgejo remote (`100.119.46.15:2222`, Tailscale) is unreachable — the
self-hosted box appears offline. GitHub is fully synced. Forgejo is behind
by 4 commits (`08c40bf`, `74fe889`, `9aa71f4`, `1df6c2e`).
**Action:** run `git push forgejo master` once the box is back online —
it's a fast-forward, no `--force` needed.

## Decisions Made

- **/sessions pagination (#17):** server renders only the first 50 sessions;
  remaining pages load lazily via `GET /sessions/rows` (HTML fragments) behind
  a "Load more" button. Row markup extracted into shared `SESSION_ROWS_TEMPLATE`.
  Chosen over wiring the JSON `/api/v1/sessions` API into the frontend because
  the API summary serializer lacks `prompt_outline` and `tag`/date filters.
- **Vendored assets (#19):** Tailwind 3.4.16 + highlight.js 11.9.0 checked into
  `ai_history/interfaces/static/`, served by Flask's static route. No CDN —
  works air-gapped. `scripts/vendor_assets.py` re-downloads + SHA-256-verifies.
- **CSP after vendoring:** `script-src` stays nonce-only; `style-src` keeps
  `'unsafe-inline'` because the Tailwind JIT injects an un-nonced runtime
  `<style>`. Style injection ≠ script injection risk — accepted trade-off.
- Dropped the Source Code Pro Google Font (local monospace fallback in CSS).

## Files Changed This Session

| File | Change |
|------|--------|
| `ai_history/interfaces/web.py` | `/sessions` paginates (50/page); new `/sessions/rows` fragment route; `import math` hoisted; Flask `static_folder`; CSP drops CDN origins |
| `ai_history/interfaces/web_templates.py` | new `SESSION_ROWS_TEMPLATE` partial; `/sessions` "Load more" button + JS; `/static/` asset URLs; Google Font removed |
| `ai_history/interfaces/static/*` | vendored tailwind-3.4.16.min.js, highlight-11.9.0.min.js, highlight-github-11.9.0.min.css |
| `scripts/vendor_assets.py` | new — re-download + SHA-256-verify pinned assets |
| `pyproject.toml` | `[tool.setuptools.package-data]` ships static dir in wheel |
| `tests/test_sessions_pagination.py` | new — 7 pagination tests |
| `tests/test_vendored_assets.py` | new — 9 offline/vendoring tests |
| `tests/test_csp_nonces.py` | updated for vendored-asset CSP (no-CDN, style-src policy) |
| `README.md`, `CLAUDE.md` | note assets are vendored, not CDN |

## Current State

- **Tests**: 700 passing, 80.78% coverage
- **GitHub issues**: 7 open (down from 32) — **all P0/P1 closed**
- **GitHub** `master` at `1df6c2e`; **Forgejo** behind (host offline — see above)

## Open Issues (7 remaining — all P2/P3, not release-blocking)

| # | Label | Issue |
|---|-------|-------|
| 32 | p3 | Single SQLite source of truth (v3 milestone) |
| 31 | p2 | Decompose mcp.create_server() — 445 LOC |
| 30 | p2 | Move HTML from web_templates.py to Jinja2 template files |
| 29 | p2 | MCP-over-HTTP transport (streamable-http) |
| 28 | p2 | Shareable static HTML export per session |
| 27 | p2 | ai-history digest — weekly summary command |
| 24 | p2 | Scoped MCP search (user_only / assistant_only / tool_results) |

## Aider extractor (#51) — done this session

- `ai_history/extractors/aider.py`: parses `.aider.chat.history.md`
  (one file per project, discovered under `$HOME`). Each
  `# aider chat started at ...` block → one session. `#### ` = user,
  `> ` = tool, un-prefixed = assistant. Hash-based stable session IDs.
- `Tool.AIDER` added; registered in factory + `tooling`/`security`
  allowlists + web `TOOL_STYLES`. 15 tests + contract-suite coverage.

## Next Steps (recommended order — all optional enhancements)

1. **#27 — Digest command**: `ai-history digest --since 7d` → summary of
   recent sessions (LLM-backed).
2. **#24 — Scoped MCP search**: add `scope=user_only|assistant_only|tool_results`
   to the MCP search tool.
3. **#28 — Static HTML export**: `ai-history export --html <session>` →
   self-contained shareable HTML file.
4. **#30 — Jinja2 file migration**: move templates out of `web_templates.py`
   strings into real `.html` files (large refactor, cosmetic).

Release-blocking work is complete: the project is in a publishable state.
