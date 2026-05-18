# HANDOFF — ai-history — 2026-05-18

> Claude: update this before session ends with /compact or on Stop.

## Current Task

The **shared agent-memory vision** (#33) is the active direction. Its
foundation — issue #44, "single SQLite source of truth" — is **done** across
4 PRs. ai-history is now both a session viewer *and* a cross-tool memory store.

## Forgejo remotes

- `forgejo` — `ssh://git@100.119.46.15:2222/...` (Tailscale, only when the
  self-hosted box is online).
- `forgejo-https` — `https://git.erdlabs.com/erdna/ai-history.git` (reachable
  via Cloudflare; needs a Forgejo access token — `git-credential-libsecret`
  caches it after the first `! git push forgejo-https master`).
- **GitHub is the synced remote**; Forgejo is behind — push when convenient.

## The vision (#33) — read this first

ai-history → tool-übergreifendes **geteiltes Gedächtnis** für KI-Agenten:
EINE lokale DB, aus der jeder Agent/Tool/MCP/Skill liest UND schreibt.
CEO-Mandat des Users: bei Bedarf neues Repo/Namen, Research-Agenten,
Spektrum auf alle Tools mit Sessions erweitern. Details in Issue #33 +
memory `vision_shared_memory.md`.

## #44 — done this session (4 PRs)

| PR | Commit | What |
|----|--------|------|
| 1 | 4b1d781 | v2 SQLite schema + migration runner (`ai_history/storage/`) |
| 2 | b2f3c5f | dual-write: IndexBuilder mirrors sessions+messages into `index_v2.sqlite` |
| 3 | 11adf4b | `load_index()` reads v2 (JSON fallback via `AI_HISTORY_USE_V2=0`) |
| 4 | 5fa9fc2 | memory tables + `memory_write`/`memory_recall` (MCP + CLI) |

`ai_history/storage/` modules: `schema.py` (7 migrations), `writer.py`
(dual-write), `reader.py` (v2→legacy dict), `memory.py` (memory CRUD).

## Earlier this session

- **#51 Aider extractor**, **#43 digest command** (`ai-history digest`).
- **#17 /sessions pagination**, **#19 vendored Tailwind/highlight.js**.

## Current State

- **Tests**: 787 passing, ~81% coverage
- **GitHub** `master` at `5fa9fc2`
- **GitHub issues**: 5 open (all P2/P3) — #44 closed; vision tracked in #33

## Open Issues (5 P2/P3 + the open-ended #33)

| # | Label | Issue |
|---|-------|-------|
| 33 | p1 | **Vision: shared agent memory** — tracking issue, ongoing |
| 31 | p2 | Decompose mcp.create_server() — now >700 LOC |
| 30 | p2 | Move HTML from web_templates.py to Jinja2 template files |
| 29 | p2 | MCP-over-HTTP transport (streamable-http) |
| 28 | p2 | Shareable static HTML export per session |
| 24 | p2 | Scoped MCP search (user_only / assistant_only / tool_results) |

## Next Steps (vision-first, per #33)

1. **Semantic memory search** — embeddings + vector search (`sqlite-vec`)
   so agents recall thematically, not just by keyword.
2. **Populate memory_sources** — auto-link memory to the sessions/messages
   it was derived from.
3. **Web UI for memory** — browse/search memory entries in the interface.
4. **Broaden extractor coverage** — more AI tools with sessions.
5. Re-evaluate the repo-split decision now that memory exists (#33).

## Gotchas discovered

- v2 DB is located via `INDEX_PATH.parent`, not `OUTPUT_DIR` — so tests that
  patch `INDEX_PATH` stay isolated. Patch both if a test needs v2.
- Docker builds were failing: host runs systemd-resolved (`127.0.0.53`),
  unreachable from containers. Fixed by adding `"dns": ["1.1.1.1","8.8.8.8"]`
  to `/etc/docker/daemon.json` + `firewalld --reload` then `restart docker`
  (order matters). The ai-history-app container image is still old (Apr 13);
  rebuild with `docker compose build app` when the Debian mirror is responsive.
