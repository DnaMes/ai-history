# Plan — Hybrid search over the session archive (#56, remaining item)

Status: **design approved 2026-07-01** — sqlite-vec + per-session vector + RRF fusion.
Validated: sqlite-vec v0.1.9 loads and runs KNN (`float[384]`) in this env
(`enable_load_extension: True`, sqlite 3.53.3). fastembed 0.8.0 already installed;
model `BAAI/bge-small-en-v1.5` (384-dim) already used for memory.

## Goal

Add semantic retrieval to the **session** archive and fuse it with the existing
v2 FTS5 keyword search into one ranked result — so `search_history` / web
`/api/search` / `lore search` return keyword **and** meaning-based matches.
Today embeddings are wired to *memory only* (`memory_embeddings`, `_semantic_recall`);
sessions have no vector path at all.

## Design decisions (locked)

| Decision | Choice | Why |
|---|---|---|
| Vector store | **sqlite-vec** `vec0` virtual table in `index_v2.sqlite` | No new service (honors "no Postgres/Redis"), real KNN in SQL, optional dep w/ graceful fallback |
| Granularity | **Per-session** (1 vector) — Phase 1 | ~1513 vectors, tiny (~2 MB), fast build; message-level deferred |
| Fusion | **RRF** `Σ 1/(k+rank)`, k=60 | Robust, no score normalization, no α-tuning |
| Model | `BAAI/bge-small-en-v1.5` (reuse memory's) | Already installed, 384-dim, CPU-only |
| Fallback | Missing sqlite-vec **or** fastembed → FTS-only, no error | Same pattern as `embeddings_available()` |

## Non-goals (Phase 1)

- Message-/chunk-level embeddings (fills reserved `entity_type='message'` FTS later).
- Re-embedding on every reload — embed on index build, incremental only.
- Tuning α weights (RRF avoids it).

## Architecture

```
IndexBuilder.build_index()  →  writer.write_sessions()  →  [NEW] embed_sessions()
                                                              ↓
index_v2.sqlite:  search_index (FTS5)   [exists]
                  session_embeddings (vec0 float[384])  [NEW, migration 13]

search path (services/index.py::search_index):
   fts_hits  = storage.search_sessions(...)          [exists, v2 FTS5]
   vec_hits  = storage.semantic_search_sessions(...)  [NEW, sqlite-vec KNN]
   fused     = rrf_merge(fts_hits, vec_hits)          [NEW]
```

## Work breakdown (each = 1 CI-green PR, branch off `main`)

### PR 1 — vector store foundation ✅ (branch `feat/hybrid-search-vec-foundation`)
- Optional dep: `pyproject.toml` `semantic = ["fastembed>=0.3", "sqlite-vec>=0.1.9"]`.
- `storage/embeddings.py`: add `sqlite_vec_available()` guard + `load_vec(conn)` helper
  (enable_load_extension → `sqlite_vec.load` → disable). Reuse existing `embed_text`,
  `pack_vector`/`unpack_vector`.
- Migration 13 in `storage/schema.py`:
  `CREATE VIRTUAL TABLE session_embeddings USING vec0(session_id TEXT PRIMARY KEY, model TEXT, embedding float[384])`
  — guarded: skip cleanly if the extension can't load (record migration anyway so it's not retried destructively; document that vec rows are rebuilt, not migrated).
- Tests: extension loads, table creates, insert+KNN roundtrip; all skip if unavailable.

### PR 2 — populate session vectors ✅ (branch `feat/hybrid-search-populate-vectors`)
- `storage/embeddings.py` (or new `storage/session_vectors.py`): `embed_sessions(conn, sessions)`
  — one vector per session from the same text `writer.py` feeds FTS (title + message
  bodies, truncated to model's max tokens). Best-effort, mirrors `memory._store_embedding`.
- Wire into `writer.write_sessions` **after** the FTS write, inside the same
  transaction guard but non-fatal on embed failure (a bad embed never blocks the index).
- Incremental: only (re)embed sessions whose row changed — full replace is fine for
  Phase 1 (1513 rows), but key on `session_id` with `ON CONFLICT DO UPDATE`.
- Tests: after `write_sessions`, N sessions → N vec rows; fallback path writes 0 and doesn't raise.

### PR 3 — semantic search + RRF fusion
- `storage/search.py`: `semantic_search_sessions(output_dir, query, *, tool, project, limit)`
  — embed query, KNN over `session_embeddings`, join `sessions`, apply tool/project
  filter, return the same `[{"session": dict, "score": float}]` shape as `search_sessions`.
- New `storage/fusion.py`: `rrf_merge(*ranked_lists, k=60, limit=50)` — pure, unit-tested.
- `services/index.py::search_index`: when v2 + both backends available, run FTS + semantic,
  fuse with RRF; else current behavior unchanged. Add `LORE_HYBRID_SEARCH` env
  (default on when available) so it can be disabled.
- Tests: fusion ordering; a query that only semantic finds surfaces; FTS-only fallback intact.

### PR 4 — surface + consistency
- MCP `search_history`: no signature change (fusion is transparent); optional `mode`
  arg (`keyword`/`semantic`/`hybrid`, default `hybrid`) for power users.
- Web `/api/search`, `/api/v1/search`: expose `semantic_available` like memory routes do;
  no UI change required, hybrid is default-on.
- **Fix CLI drift** (found during exploration): `lore_cli.py:875` `cmd_search` bypasses
  the v2 router and hits legacy `SearchEngine` directly → route it through
  `services/index.py::search_index` so CLI, web, MCP all share one search path.
- Docs: CLAUDE.md architecture section (search data flow), CONTRIBUTING if needed.

## Risks / watch-items

- **Loadable extensions can be disabled** in some Python sqlite builds. Verified OK here;
  guard + fallback means "off" degrades to FTS-only, never crashes. Document in HANDOFF.
- **Model max tokens**: bge-small truncates ~512 tokens; per-session text far exceeds that.
  Phase-1 accepts coarse (title + head). Message-level (Phase 2) is the real fix.
- **Index staleness**: vec table lives in `index_v2.sqlite`, already staleness-guarded by
  `reader.py`. Embed on build keeps it in lockstep with FTS.
- **`.venv` shebang broken** (points at old `ai-history` path, Rename-Altlast) — unrelated
  cleanup, but rebuild the venv before shipping so `[dev]`/`[semantic]` installs are clean.

## Verification (per Core Rule 1 — real output, not "should work")

Each PR ships with: pytest green (3.11/3.12), and for PR 3/4 a live check —
`lore search "<semantic-only phrase>"` returns a session that keyword search misses,
pasted into the PR. Final: MCP `search_history` handshake with `mode=hybrid` over the
real `~/.lore` archive.
