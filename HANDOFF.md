# HANDOFF — ai-history — 2026-05-18

> Claude: update this before session ends with /compact or on Stop.

## Current Task

A four-agent QA review (architecture, security, accessibility, test
coverage) plus a hands-on UI inspection produced 16 issues (#34–#49).
**All 16 are now fixed and closed.** The project is in materially better
shape than the "787 tests green" claim implied.

## What the review found and how it was fixed

| Issue | Severity | Fix (commit) |
|---|---|---|
| #34 search read legacy DB while load_index read v2 | P0 | search routed through v2 search_index (660f520) |
| #35 v2 messages incomplete after incremental sync | P0 | reused_sessions written full + messages_synced flag (2b90f5c) |
| #36 no v2 staleness check; generated_at unset | P0 | store_meta + staleness compare (9163215) |
| #37 coverage omit list hid 4 extractors | P1 | omit trimmed, 61 fixture tests (commit w/ #39) |
| #38 mobile layout broken | P1 | off-canvas drawer (4bdaa96) |
| #39 WCAG AA failures | P1 | contrast/modals/markup (commit w/ #37) |
| #40 no concurrency test, no busy_timeout | P1 | busy_timeout + 10 tests (e554dc8) |
| #41/#42/#45 security hardening | P2 | file perms, memory caps, CSRF guards (4d08c5f) |
| #44/#46/#49 dead code + migrations + polish | P2 | (e554dc8, 4bdaa96) |
| #50 CSP nonce left the UI unstyled | P0-class | style-src unsafe-inline only (4bdaa96) |

The #50 CSP bug was the scariest find: a nonce in `style-src` made CSP3
ignore `'unsafe-inline'`, blocking every Tailwind-injected style — the
whole UI rendered unstyled. Caught only by a hands-on headless screenshot,
not by the suite. Fixed; consider a render-smoke-test as follow-up.

## Current State

- **Tests**: 887 passing, ~82% coverage (real — the 4 dark extractors
  are now counted, not omitted)
- **GitHub** `master` at `4bdaa96`; issues #34–#50 all closed
- **`AI_HISTORY_USE_V2` is back to default-on** — the v2 store is now
  consistency-checked and concurrency-hardened
- Open issues: #33 (vision tracking), #24/#28/#29/#30/#31 (P2 enhancements)

## Storage layer (issue #44) — now solid

`ai_history/storage/`: schema (9 migrations, idempotent ALTERs),
writer (dual-write, messages_synced), reader (staleness check), search
(v2 FTS), memory (agent memory + input caps). WAL + busy_timeout.

## Next Steps

1. **#33 vision** — semantic memory search (embeddings / sqlite-vec),
   memory_sources auto-linking, a web UI for memory.
2. Remaining P2 enhancements (#24 scoped MCP search, #28 static HTML
   export, #30 Jinja file migration, #31 mcp decomposition).
3. Optional: headless render-smoke-test so a CSP/asset regression like
   #50 is caught automatically.

## Gotchas

- The Docker container on port 5000 runs an old (Apr-13) image — local
  dev must use a different port. Rebuild needs the Debian mirror
  reachable; `daemon.json` DNS fix is in place.
- v2 DB is located via `INDEX_PATH.parent`; tests patching `INDEX_PATH`
  stay isolated. Patch `web_data.INDEX_PATH` (not just `web.INDEX_PATH`)
  for anything that calls `load_index()`.
