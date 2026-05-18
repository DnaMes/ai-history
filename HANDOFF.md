# HANDOFF — ai-history — 2026-05-18

> Claude: update this before session ends with /compact or on Stop.

## Current State — production-ready, released 2.2.0

All open bug/security/P0/P1 issues are closed. The project is in a
publishable, production-usable state. Tagged **v2.2.0**.

- **Tests**: 945 passing, 83.85% coverage
- **GitHub** `master` at `2607602`, tags `v2.1.0` + `v2.2.0`
- **Open issues**: 4 — all intentional, none blocking:
  - #33 — Vision tracking issue (permanent)
  - #48, #30, #29 — `roadmap`-labelled, deferred with documented rationale
    (JSON retirement, Jinja-file migration, MCP-over-HTTP) — not blockers

## What this session delivered

- **Vision (#33)**: v2 SQLite store, cross-tool agent memory, semantic
  recall (optional `[semantic]` extra), `/memory` web page.
- **Features**: scoped MCP search (#24), standalone HTML export (#28),
  `ai-history digest`, Aider extractor, package versioning + `--version`.
- **Refactors**: `services/` layer (killed 4 duplications, fixed the
  mcp→web_data inversion), decomposed `mcp.create_server()` 550→15 lines.
- **Two QA review rounds** (architecture/security/accessibility/test):
  16 issues found+fixed in round 1, 5 hardening fixes in round 2.

## Storage architecture (issue #44 — complete)

`ai_history/storage/`: schema (10 migrations, idempotent), writer
(dual-write), reader (staleness check), search (v2 FTS + scoped), memory
(agent memory + caps), embeddings (optional semantic). WAL + busy_timeout.
`ai_history/services/`: cache, extraction (the Sync engine), index.

## Roadmap (deferred, not blocking — see the labelled issues)

1. #33 vision next steps: `memory_sources` auto-linking (Memory ↔ source
   sessions), then the repo-split decision.
2. #48 JSON retirement, #30 Jinja files, #29 MCP-over-HTTP — when the
   need is concrete.
3. Minor QA follow-ups noted by the agents: real-extractor end-to-end
   test, exporter protocol unification, IndexBuilder relocation.

## Gotchas

- Docker container on port 5000 runs an old image; local dev uses a
  different port. `daemon.json` DNS fix is in place.
- v2 DB located via `INDEX_PATH.parent`; patch `web_data.INDEX_PATH`
  (not just `web.INDEX_PATH`) for anything calling `load_index()`.
- `fastembed` is installed in this venv; semantic tests run for real.
  Without it they skip cleanly (CI-safe).
- Forgejo remote `forgejo-https` (git.erdlabs.com) needs a fresh token
  to push; GitHub is the synced remote.
