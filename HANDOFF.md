# HANDOFF — Lore — 2026-06-25

> Claude: update this before session ends with /compact or on Stop.

## Session 2026-06-24/25 — Professionalization push (Axis 1 + rename + render rebuild)

All work landed on **master** via PRs. Branch each new piece off master.

**Merged this session:**
- **#58** Axis-1 data completeness — claude.py 500-char tool-result truncation removed (1326 results recovered), tool results attached to their tool_call as `output` (3999/4005), skip-count tracking (#1e), `LORE_MIN_USER_PROMPTS` env override, doc hygiene.
- **#60** Full rename `ai_history` → `lore` (v2.4.0) — package/modules/env-vars (`LORE_*` with back-compat alias shim in `lore/__init__._alias_legacy_env`), metrics, Dockerfile, docs. `import ai_history` now fails by design. Legacy `~/.ai-history` refs in `utils/paths.py`+`web_data.py` kept on purpose (auto-migration path).
- **CI fix** (in #58) — ci.yml had never run green: black→ruff, added pytest-cov, bandit skips (B310/B608 documented, SHA1 `usedforsecurity=False`).
- **#61** #53 Phase 0 — `session_view_prep.py`: render from structured `tool_calls` (prose + paired tool cards), not regex re-parse. Verified: 295 call + 147 result pills, 0 `[Tool:` leaks, 23380-char result renders.
- **#63** #53 Phase 1 — assistant model + token chips (conditional), slate card accent.
- **#64** #53 Phase 2 — Edit/Write **diff rendering** (`format_diff`/`_diff_rows`, difflib), green/red rows, nh3-safe. Verified: 16 edits → 16 diff blocks.

**Suite green throughout, coverage ~83.8%, ruff+bandit clean.**

### NEXT (do on ai-workstation): #53 Phase 3 + open issues
- **#53 Phase 3** — Sticky-TOC scroll-spy (TOC partly exists, `web_templates.py:1655`), Tool-Burst-Folding (≥3 consecutive calls), Duplicate-Folding (UMBAU §7). Build in `session_view_prep.py` (burst/dup grouping) + template + CSS.
- **#62** per-message tokens dropped in served path → Phase-1 chips only show with `?live=1`. Fix: hydrate served messages from v2 store (`storage/reader.py`, `tokens_json` already persisted) instead of flat index.
- Other open issues: #54 opencode 50k truncation, #55 parametrize contract test, #56 differentiation options (tags/hybrid-search/resume/cost), #57 raw-vs-import gap report.
- UMBAU §6 Fidelity-Toggle intentionally skipped — existing Clean/Ultra toggles cover it.

### Gotchas (this session)
- `lore-web`/`lore-mcp` entry points are broken pre-existing (`lore/cli/{web,mcp}.py` are 0-byte stubs; `main`/`main_sync` undefined). Run the app via `lore.interfaces.web:app` (gunicorn) directly. Worth fixing.
- Per-message tokens: only opencode/gemini populate them; claude/codex/cursor don't (chips stay absent, by design).
- Force-push + permission-rule self-grant are hard-blocked by safety hook + auto-mode classifier — user must run those.

## Current State

Product name is **Lore** (Python import package is now `lore` — renamed from `ai_history`).
Version **2.4.0**. **853 sessions** indexed across 7 tools.

- **Repo**: `~/projects/lab/ai/lore` (renamed from `ai-history` this session)
- **GitHub**: `DnaMes/lore` — single remote, Forgejo deleted
- **Data**: `~/.lore` (old `~/.ai-history` wiped, fresh-synced from source)
- **Docker**: `lore-app` on port 5000, `docker compose up -d app`
- **Sync**: systemd user timer `lore-sync.timer` every 30min (Nice=10, MemoryMax=4G)
- **Obsidian vault**: `~/ObsidianVault/Projects/lab/lore/`

## Session 2026-06-24 — Data-completeness foundation (Axis 1)

Branch `feat/data-completeness-prep-layer` (off `master`). Commit `87d0107`. Suite green, coverage 83.6%.

**Done & verified:**
- **Removed claude.py 500-char tool_result truncation** — was real data loss. Verified on live data: 1326 of ~4000 tool results exceed 500 chars, now kept in full.
- **Attached tool results to their tool_call** as `output` (+ `status="error"`), threaded by `tool_use_id` across JSONL records. 3999/4005 calls now carry structured output. This is the data foundation the render-rebuild (#53) needs — no more regex re-parse required.
- **Skip-count tracking** (`base.py.skip_counts`) — filtered sessions are tallied per reason instead of silently dropped (#1e). Surfaced in `extraction.py` per-extractor log + report entries.
- **`AI_HISTORY_MIN_USER_PROMPTS` env override** — lower the threshold without flipping the import profile.
- **warp.py** silent `except: pass` → logged OSError.
- **Doc hygiene**: CLAUDE.md / AGENTS.md / README / docs/ROADMAP — ruff (not black/isort/flake8), single `app` Docker service + `lore-app` (no postgres/redis), `lore-*` CLI names, Lore naming.

**Verified-already-done (prompt assumed open):** CODE_OF_CONDUCT ✓, 3-cmd quickstart ✓, `_new` module rename ✓ (`lore-web`=`lore.cli.web`), ruff in pre-commit ✓, v2 schema (10 migrations incl. memory_embeddings + memory_tags) ✓, MCP 10 tools ✓, all 10 extractors have test files ✓. **safe_copy_db /tmp leak: NOT a leak** — both callers (cursor/warp) already clean up in `finally`; 0 leaked files on disk.

**Deferred → GitHub issues:** #53 render-rebuild + prep-layer (Axis 2 / UMBAU.md), #54 opencode 50k truncation, #55 parametrize contract test, #56 differentiation options (tags/hybrid-search/resume/cost), #57 raw-vs-import gap report.

**Next:** PR `feat/data-completeness-prep-layer` → `main`; then start #53 (prep-layer) as the next session's foundation.

## What This Session Delivered (2026-05-26)

### Rebrand & Cleanup
- Renamed local folder `ai-history` → `lore`, Obsidian vault too
- Deleted Forgejo repo (0 issues, 0 PRs — was a dead mirror)
- Wiped both `~/.lore` + `~/.ai-history`, fresh-synced from tool source dirs
- Removed ghost Docker containers `ai-history-db` + `ai-history-redis` + volumes
- Removed old systemd service `ai-history-sync`, replaced with `lore-sync.timer`

### Laptop Freeze Fix
- Root cause: old `ai-history-sync.service` (while-true bash loop) ran `export --all` which parsed all sessions TWICE (O(2N)), hit 9.3 GB RAM, swapped system
- Fixed: CLI default `--output-dir` now uses `lore_home()` (→ `~/.lore`); removed the 2nd extractor loop in `cmd_export` when no filter is active (peak 2.5 GB now)
- New timer has `MemoryMax=4G`, `Nice=10`, `IOSchedulingClass=idle`, `TimeoutStartSec=30min`

### Claude Code Subagent Coverage (46 → 333 sessions)
- `extractors/claude.py` now walks `*/subagents/*.jsonl` (was non-recursive glob)
- Subagent sessions get `[subagent agent-XXX]` title prefix, thread_id links to parent
- Session IDs use `<parent-uuid>:agent-XXX` format — validator updated to accept it
- Deduplication: Claude Code sometimes stores same sessionId in 2 project dirs; extractor keeps newer mtime

### v2 Store Fixed
- The UNIQUE constraint error on `sessions.id` was caused by the above duplicate session IDs
- Writer now uses `INSERT OR REPLACE` as safety net
- v2 store goes from 0 → 794 sessions; search now uses v2 with BM25 scores

### Search, Sync Button, Themes
- Search returned [] because v2 was empty but reported as "available"; now falls back to legacy when v2 is stale or empty
- Sync button showed no progress for 60s; now emits per-second updates with session counter
- Themes stripped from 7 (catppuccin default!) to Light + Dark only

### Session Quality Filter
- `MIN_USER_PROMPTS` bumped from 1 → 3 (relaxed profile); strict → 5
- `lore prune --max-prompts 2` applied once: 2121 → 800 sessions
- Test suite pinned to `MIN_USER_PROMPTS=1` via `conftest.py` autouse fixture

### UI Fixes (from prior compacted session)
- TOC scroll: native `scrollIntoView` + jumpLock (observer was hijacking scroll)
- Pagination: 8 MB → 740 KB initial load; lazy `load more` fragments
- Session caching: stat-keyed LRU on export file → 6.3s → 0.08s warm
- Stats page rebuilt as real activity dashboard (was showing all-zero token costs)
- Conversation CSS theme variables consolidated (white-card-on-dark-bg bug)

## Files Changed (key ones)

- `lore/extractors/claude.py` — subagent walk, dedup, `_add_or_replace_newer`
- `lore/extractors/base.py` — `MIN_USER_PROMPTS=3`
- `lore/utils/security.py` — `_SUBAGENT_RE` pattern in validator
- `lore/storage/writer.py` — `INSERT OR REPLACE`
- `lore/services/index.py` — v2 staleness check + empty-result fallback
- `lore/services/extraction.py` — per-second progress callbacks in sync loop
- `lore/interfaces/web_templates.py` — themes, TOC scroll, pagination, CSS
- `lore/interfaces/web.py` — session cache, pagination, fragment route
- `lore_cli.py` — `lore_home()` default, single-pass export
- `tests/conftest.py` — `MIN_USER_PROMPTS=1` autouse fixture
- `~/.config/systemd/user/lore-sync.{service,timer}` — new timer-based sync
- `docker-compose.yml`, `Dockerfile` — lore-app branding

## Decisions Made

- **Keep Lore**: claude-mem/mem0/MemPalace don't replace it (different use cases)
- **No server hosting**: Lore reads local tool dirs, server would need dir sync
- **Single remote (GitHub)**: Forgejo was dead weight
- **MIN_USER_PROMPTS=3**: cuts 62% of trivial sessions without losing real ones
- **v2 store as primary search**: legacy JSON search is fallback only

## Gotchas

- Shell cwd resets to the old `ai-history` path between Bash calls (phantom inode); use absolute paths
- `fastembed` is installed in `.venv`; semantic tests run for real
- Docker container has no `curl` — can't `docker exec ... curl` for cache-clear
- The `lore prune` CLI writes a `v2 dual-write skipped` warning if run when v2 is stale — harmless, next sync fixes it
- Subagent sessions have `project_path: None` in the index — the extractor sets it via `_decode_project_name` but `IndexBuilder` doesn't always carry it through

## Next Steps

1. **Tag v2.4.0** — all the above is committed but untagged
2. **`project_path` on subagent index entries** — currently `<missing>`, should inherit from parent project dir (cosmetic but affects project-filter in UI)
3. **Roadmap issues still open**: #33 vision, #48 JSON retirement, #30 Jinja migration, #29 MCP-over-HTTP
4. **Design/UI polish** — user has repeatedly said the UI looks "billig"; consider a real design pass with the `ui-ux-pro-max` skill
5. **v2 store backfill** — 794 sessions have `messages_synced=1` but incremental-sync reused entries have `messages_synced=0`; the backfill logic (#35) should run once
