# HANDOFF — Lore — 2026-07-02 (hybrid search shipped end-to-end, #56 closed)

> Default branch is **main** (renamed from master 2026-07-01). Remote is `github`, not `origin`.
> Update this before session ends.

## ▶ #96 — DONE (PR #102). Root cause was broader than framed.

**PR #102** (`fix/96-indexbuilder-streaming`) ships the cold-rebuild fix.
Investigation found the ~1.9 GB was **three** contributors, not just list
retention (measured peak VmHWM on the real ~980-session archive):

| Path | Before | After |
|---|---|---|
| cold full rebuild (the OOM-risk case #96 reports) | 2084 MB | **1404 MB** |
| web-reload path (non-incremental) | 2040 MB | **1421 MB** |

1. **build_index list retention (~500–600 MB, unbounded term)** — fixed:
   `_MultiWriter` single-pass fan-out (`lore/exporters/index.py`), callers pass
   generators, `StreamingV2Writer` for v2 (`lore/storage/writer.py`).
2. **139 MB VSCode chat file `json.load` spike (31→1226 MB)** — fixed: 25 MB
   per-session-file cap in `lore/extractors/vscode.py` (`MAX_SESSION_FILE_BYTES`).
3. **opencode internal dedup dict (~425 MB)** — follow-up **#104**.

**Warm incremental** still peaks ~2.0 GB (holds reused full sessions to re-write
v2 message rows, #35) → follow-up **#103** (needs incremental v2 writes, like
#95's incremental embedding). Neither follow-up is the OOM cold case.

1120 tests pass (was 1109 + 11 new). Design doc + steelman under
`docs/superpowers/specs/2026-07-02-indexbuilder-streaming-design.md`.

---

## TL;DR — hybrid search (#87) shipped in 4 PRs; #56 umbrella closed

**Session 2026-07-01/02:** `master`→`main` rename (GitHub API rename, PR #65 closed as
stale, CI/docs refs fixed), venv rebuilt (was still the old `ai-history` editable install
on a broken path — now `lore 2.4.0` on Python 3.12), and **#87 hybrid search** built
end-to-end per `docs/PLAN-hybrid-search.md`:

| PR | What |
|---|---|
| #88 | sqlite-vec foundation — vec0 `session_embeddings` table, guarded outside MIGRATIONS |
| #89 | one embedding per session populated on index write (post-FTS-commit, best-effort) |
| #90 | `semantic_search_sessions` (KNN) + `rrf_merge` fusion wired into `search_index` |
| #91 | CLI drift fixed — `lore search` now uses the shared v2 router; CLAUDE.md documents the flow |

Suite **1102 passed**, coverage ~84.8%, all CI green. Design: sqlite-vec in
`index_v2.sqlite`, per-session bge-small 384-dim vectors, RRF (k=60), `[semantic]`
optional extra with FTS-only fallback, `LORE_HYBRID_SEARCH=0` escape hatch.
Verified end-to-end over the real archive: 7/10 hits for a conceptual query found
only by semantic search. **#56 + #87 closed; follow-up #92** (distance cutoff +
message-level embeddings, Phase 2).

⚠️ **Syncthing corrupted `.git` four times this session** (invalid refs/reflogs, one
missing blob). **Fixed for good on 2026-07-02**: `/lab/ai/lore` added to
`~/projects/.stignore` on BOTH machines (per-device file!) — lore is no longer
Syncthing-synced at all; git push/pull is the only sync. Repair recipe for ref
corruption lives in the project memory (`ai-workstation-syncthing-mirror`).

**QA session + fixes 2026-07-02** (deep pass over hybrid search, then fixed all findings):
- ✅ good: warm search 70–85 ms, cold first search 0.85 s; FTS-injection/unicode/5k-query
  edge cases clean; MCP `search_history` returns fused RRF results.
- **#94 → #100 merged**: Docker installs `[semantic]` + pre-downloads bge-small at build
  time; `/api/build-info` now reports `semantic.*`. ⚠️ **Offline image smoke NOT run** —
  local Docker daemon DNS is broken (can't resolve deb.debian.org, no image builds here).
  **#101 tracks running it in a working Docker env before trusting prod hybrid search.**
- **#95 → #99 merged**: reload no longer times out. `embed_sessions` is now incremental
  (migration 13 `session_embedding_meta`, `LORE_EMBED_BUDGET_SECONDS` default 60s); only
  changed sessions re-embed. Also fixed a latent bug: incremental sync's full DELETE used
  to wipe every vector. Live web reload **92 s, done** (was 382 s → timeout/abort).
- **#96 (p2, still open)**: reframed after investigation — the ~1.9 GB is NOT the model
  (263 MB); it's the IndexBuilder holding all ~960 sessions in RAM (1740 MB with zero
  embedding). Pre-existing, unrelated to hybrid search. Needs IndexBuilder streaming.
- **#97 → #98 merged**: `/api/v1/search` now honors + validates `scope`.

Suite **1109 passed**; `main @ cdcccc3`.

**Open roadmap** (all need a direction decision): #96 IndexBuilder RAM (p2), #101 Docker
offline verify (p2), #92 hybrid-search Phase 2 (distance cutoff), #48 JSON-retirement,
#33 shared memory, #29 MCP-over-HTTP.

---

## Previous session — 2026-06-30 (QA + 11 issues + #30 Jinja, all merged)

Autonomous QA + fix sweep. **18 PRs merged** (#70–#86), each CI-green
(lint + bandit + pip-audit + tests 3.11/3.12), squash-merged to master. Suite **1063 passed**,
coverage ~83.9%. master HEAD **9017965**.

Latest round: #62, #54, #55, #57 (diagnosed), #79 (canonical tool_call shape — fixed
silently-dropped codex/copilot args), #53 (render rebuild closed), #83 (tool-burst ×N folding),
and **#56 session tags end-to-end** (#85 backend: migration 12 `session_tags` + storage CRUD +
`/api/sessions/<id>/tags` + `/api/tags` + MCP `user_tags`; #86 UI: tag-editor chips on the
session page). All remaining work is genuinely strategic architecture.

| # | Fix | PR |
|---|---|---|
| [#66](https://github.com/DnaMes/lore/issues/66) | `lore-web`/`lore-mcp` CLI entry points (were 0-byte) | #70 |
| [#68](https://github.com/DnaMes/lore/issues/68) | strip `<local-command-caveat>` title leak + command noise | #71 |
| [#67](https://github.com/DnaMes/lore/issues/67) | cost dashboard: persist per-session token total (migration 11) | #72 |
| [#69](https://github.com/DnaMes/lore/issues/69) | antigravity/copilot drops surfaced as skip reasons | #73 |
| — | `[dev]` extra + MCP serverInfo version → `lore.__version__` | #74 |
| [#67](https://github.com/DnaMes/lore/issues/67)↳ | cost dashboard `untokened_count` (no silent drop) | #75 |
| [#30](https://github.com/DnaMes/lore/issues/30) | extract 13 Jinja templates → `lore/templates/*.html`, env built once | #76 |
| [#62](https://github.com/DnaMes/lore/issues/62) | served-path per-message tokens/model from v2 store (chips without `?live=1`) | #77 |
| [#54](https://github.com/DnaMes/lore/issues/54) | stop truncating opencode tool output at 50k (2M cap + `truncated` flag) | #78 |
| [#55](https://github.com/DnaMes/lore/issues/55) | parametrized extractor contract tests (tool_calls shape, empty-HOME) | #81 |
| [#57](https://github.com/DnaMes/lore/issues/57) | diagnosed: raw→import gap is 100% MIN_USER_PROMPTS filtering, no data loss (closed) | — |

- **Version** 2.4.0 · **Repo** `~/projects/lab/ai/lore` · **GitHub** `DnaMes/lore` (default `master`, HEAD **5c77393**)
- **Data** `~/.lore` · **Docker** `lore-app` :5000 (`gunicorn --workers 1`)
- `lore-web --port 5057` works; `pip install -e ".[dev]"` sets up the dev env.
- Cost dashboard real; token/model chips render without `?live=1`; templates are files now.

## Open issues — all genuinely strategic, need a product/design conversation first

Only architecture/design work left:

- **[#56](https://github.com/DnaMes/lore/issues/56)** — umbrella, **3 of 4 items shipped** (Resume, cost dashboard, tags end-to-end). Remaining: **hybrid search over the archive** — extend `memory_embeddings` (migration 10) semantic retrieval to the session archive. Sizeable: embedding-model + index-size tradeoffs, retrieval pipeline. Split into its own issue + close this umbrella when picked up.
- **[#48](https://github.com/DnaMes/lore/issues/48)** JSON-retirement exit criteria — when the legacy index.json path is fully retired in favour of v2 (architecture decision).
- **[#33](https://github.com/DnaMes/lore/issues/33)** shared-memory vision — architecture.
- **[#29](https://github.com/DnaMes/lore/issues/29)** MCP-over-HTTP transport — feature.

All four need a direction decision (which embedding model? when to drop JSON? HTTP transport priority?) before code. Not loop-fixable — they're the genuine roadmap.

## ⚠️ repo-autosync gotcha (cost me a near-miss this session)

`~/bin/repo-autosync.sh` runs `git add -A` then commits to `autosync/<host>` and `reset --soft`s —
so it **leaves everything staged** in the working tree, and Syncthing can create
`*.sync-conflict-*` branches. Twice this session that pulled `docs/` (untracked) and an old branch's
changes into a feature commit; I had to soft-reset and re-stage explicitly. **Before any commit on
this repo, run `git diff --cached --name-only` and stage only your intended files** — don't trust a
clean-looking `git add <file>`; the autosync may have pre-staged other things. The autosync branches
(`autosync/fedora`, `autosync/ai-workstation`) are user infra, left untouched.

## Verified outcomes (real, not "should work")

- **#66** — `lore-web --port 5058` → /api/health + / = 200; `lore-mcp` answers a JSON-RPC initialize handshake.
- **#68** — example caveat session: `<title>` + `<h1>` + body (default & `?live=1`) all clean; a legit live title still wins; nh3 XSS tests still green.
- **#67** — after a full index rebuild, `/api/stats/costs` returns total_tokens=5,569,949,748, session_count=719, by_tool (claude 58M / gemini 139M / opencode 5.37B).
- **#69** — antigravity skip_counts = {no_task_md: 12, too_few_user_prompts: 7}; copilot's 2 sessions are real but single-prompt (correctly filtered). Neither had a lying is_available — the bug was silent drops, now surfaced.

## Findings worth a follow-up — ALL SHIPPED (verified 2026-07-01)

Every item previously listed here is done; kept for the trail:

- **`[dev]` extra** — present, `pyproject.toml:43` (`dev = [...]`).
- **Cost dashboard "N without token data"** — `untokened_count` surfaced, `web.py:1006/1067`.
- **MCP serverInfo version** — uses `__version__`, `server.py:67`; live handshake returns `2.4.0`.
- **#30** — Jinja extraction done; 13 files under `lore/templates/`, `web_templates.py` gone.
- Planning docs `docs/EXECUTION-PROMPT.md`, `docs/UMBAU.md` — committed and tracked.

## Pre-existing open issues still relevant

- **#30** Jinja extraction (`web_templates.py` = 2036-LOC Python string) = the "make it leaner" item. Body references old `ai_history/` path.
- **#62** per-message token chips only with `?live=1` — partially overlaps the now-fixed #67 (index now carries `tokens`); revisit whether the served-path chips can reuse it.
- **#57** raw→imported gap, **#56** differentiation options (tags/bookmarks/hybrid-search/resume), **#55** parametrized contract test, **#54** opencode 50k truncation, **#33/#48/#29** roadmap.

## How to run the web UI locally

```bash
cd ~/projects/lab/ai/lore
FLASK_SECRET_KEY=devtest .venv/bin/lore-web --port 5057    # now works (#66 fixed)
# then: curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:5057/api/health  → 200
```
Or Docker: `docker compose up -d app` → :5000. After token/extractor changes, rebuild the
index with `lore export --all` (also rebuilds the v2 store + cost data).

Live extractor probe (per-tool available + session count + skip reasons):
```bash
.venv/bin/python -c "
from lore.extractors import claude, codex, opencode, cursor, gemini, antigravity, vscode, warp
for m in (claude,codex,opencode,cursor,gemini,antigravity,vscode,warp):
    import inspect
    c=[x for _,x in inspect.getmembers(m,inspect.isclass) if x.__module__==m.__name__ and x.__name__.endswith('Extractor')][0]()
    ok=c.is_available(); n=sum(1 for _ in c.extract_sessions()) if ok else '-'
    print(f'{m.__name__.split(chr(46))[-1]:12} available={ok} sessions={n} skips={dict(getattr(c,\"skip_counts\",{}))}')
"
```

## Gotchas (still valid)

- Default remote branch is **`main`** (renamed from `master` on 2026-07-01; the old `master` ref is gone).
- gunicorn is **not** in `.venv` (Docker image only); `lore-web` uses the Flask dev server locally.
- Test deps are **not** in pyproject (no `[dev]` extra) — fresh venvs need `pip install pytest pytest-cov coverage fastembed` by hand (follow-up to fix).
- Tailwind console warning ("cdn.tailwindcss.com should not be used in production") is the vendored dev build's banner — cosmetic.
- Subagent sessions have `project_path: None` in the index (cosmetic, affects project filter).
- ~~Syncthing mirrors this repo to ai-workstation incl. `.git`~~ **No longer true (2026-07-02):** lore is in `~/projects/.stignore` on both machines — Syncthing skips it entirely; sync via git push/pull only.

## ai-workstation — synced to latest master (cca6def)

- Repo at `master` HEAD **cca6def** (all 4 fixes), Syncthing + git agree.
- Remote = **HTTPS** (`https://github.com/DnaMes/lore.git`) + `gh` credential helper (the
  `github-personal` SSH alias is laptop-only). `git pull`/`push` work without SSH keys.
- `.venv` built (python 3.12.3), editable install + test deps present, suite verified green there.

## Next session start (on ai-workstation)

1. `ssh ai-workstation`, `tmux attach -t ai` (or new), `cd ~/projects/lab/ai/lore`.
2. `git pull` (already up to date as of this handoff).
3. `.venv/bin/python -m pytest tests/ -q` — confirm green baseline.
4. Pick a follow-up from "Findings worth a follow-up" above (e.g. add `[dev]` extra, or #30 Jinja),
   or a roadmap issue. Branch off main, never commit to main directly without CI.

---

<details><summary>Previous handoff — 2026-05-26 (rebrand + data foundation)</summary>

Product **Lore** (import package `lore`). Rebrand from `ai-history`, Forgejo deleted, data
re-synced to `~/.lore`, laptop-freeze fix (single-pass export + memory-capped systemd timer),
Claude subagent coverage 46→333, v2 store fixed (INSERT OR REPLACE), search v2-primary,
MIN_USER_PROMPTS=3. Axis-1 data-completeness (removed claude.py 500-char truncation, structured
tool_call outputs threaded by tool_use_id, skip-count tracking). See git history for detail.

</details>
