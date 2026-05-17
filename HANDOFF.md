# HANDOFF — ai-history — 2026-05-17

> Claude: update this before session ends with /compact or on Stop.

## Current Task

Project finalization for public release — **all P0/P1 closed**; working
through optional P2/P3 enhancements. Aider extractor (#51) and digest
command (#43) done this session. 6 P2/P3 issues remain, none release-blocking.

## Forgejo remotes

- `forgejo` — `ssh://git@100.119.46.15:2222/...` (Tailscale, only when the
  self-hosted box is online).
- `forgejo-https` — `https://git.erdlabs.com/erdna/ai-history.git` (added
  this session; reachable via Cloudflare, needs a Forgejo access token —
  `git-credential-libsecret` caches it after the first `! git push`).

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

- **Tests**: 716 passing, 81.18% coverage
- **GitHub issues**: 6 open (down from 32) — **all P0/P1 closed**
- **GitHub** `master` at `327acf8`; **Forgejo** sync via `forgejo-https`

## Open Issues (6 remaining — all P2/P3, not release-blocking)

| # | Label | Issue |
|---|-------|-------|
| 32 | p3 | Single SQLite source of truth (v3 milestone) |
| 31 | p2 | Decompose mcp.create_server() — 445 LOC |
| 30 | p2 | Move HTML from web_templates.py to Jinja2 template files |
| 29 | p2 | MCP-over-HTTP transport (streamable-http) |
| 28 | p2 | Shareable static HTML export per session |
| 24 | p2 | Scoped MCP search (user_only / assistant_only / tool_results) |

## Done this session

- **#51 Aider extractor** — `ai_history/extractors/aider.py` parses
  `.aider.chat.history.md`; `Tool.AIDER` + factory/allowlist/styles. 15 tests.
- **#43 Digest command** — `ai_history/digest.py` (pure `build_digest` /
  `format_digest`) + `ai-history digest --since 7d [--format markdown]`.
  16 tests.

## Next Steps (recommended order — all optional enhancements)

1. **#24 — Scoped MCP search**: add `scope=user_only|assistant_only|tool_results`
   to the MCP search tool.
2. **#28 — Static HTML export**: `ai-history export --html <session>` →
   self-contained shareable HTML file.
3. **#30 — Jinja2 file migration**: move templates out of `web_templates.py`
   strings into real `.html` files (large refactor, cosmetic).

Release-blocking work is complete: the project is in a publishable state.
