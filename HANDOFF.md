# HANDOFF — Lore — 2026-06-30 (QA + 11 issues + #30 Jinja, all merged)

> Continue on **ai-workstation** (`ssh ai-workstation`, VM 300 on pve-awow, tmux session `ai`).
> ✅ Workstation synced to latest master. venv built, tests green, HTTPS+gh remote.
> Update this before session ends.

## TL;DR — every easily-fixable issue is shipped; only big features/architecture remain

Autonomous QA + fix sweep across three sessions. **16 PRs merged** (#70–#84), each CI-green
(lint + bandit + pip-audit + tests 3.11/3.12), squash-merged to master. Suite **1051 passed**,
coverage ~83.9%. master HEAD **340833e**.

Latest round (this session): #62, #54, #55, #57 (diagnosed), then #79 (canonical tool_call
shape — fixed silently-dropped codex/copilot args), #53 (session-render rebuild closed as done),
#83 (tool-burst ×N folding). All open issues are now genuinely strategic.

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

Only 4 left, none autonomous-fixable:

- **[#56](https://github.com/DnaMes/lore/issues/56)** — umbrella. **2 of its 4 items already shipped**: Resume button (`/api/sessions/<id>/resume`) + token/cost dashboard (#67/#72/#75). Remaining: (a) **user-editable session tags/bookmarks** — partial infra exists (LLM-gen tags, `compute_top_tags`, `filter_sessions(tag=)`), but user-edit needs a `session_tags` table (mirror `memory_tags` migration), write API, MCP expose, and a tag-editor UI with real UX decisions; (b) **hybrid search over the archive** — extend `memory_embeddings` (migration 10) semantic retrieval to sessions. Both want a product pass; split each into its own issue when picked up.
- **[#48](https://github.com/DnaMes/lore/issues/48)** JSON-retirement exit criteria — architecture decision (when the legacy index.json path is fully retired in favour of v2).
- **[#33](https://github.com/DnaMes/lore/issues/33)** shared-memory vision — architecture.
- **[#29](https://github.com/DnaMes/lore/issues/29)** MCP-over-HTTP transport — feature.

Also open as a tracked split-out: none — #83 (burst folding) and #79 (tool_call shape) both shipped this session.

These four need you to decide direction (build user-tags? when to drop JSON? HTTP transport priority?) before code. Not loop-fixable.

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

## Findings worth a follow-up (NOT done — out of scope)

- **`[dev]` extra missing in pyproject** — test deps (pytest/pytest-cov/coverage/fastembed) aren't declared, so fresh setups install them by hand. Add `[project.optional-dependencies] dev = [...]`.
- **Cost dashboard "N without token data"** — sessions without usage (codex today) report 0 and drop out of session_count silently. Surface the count in the dashboard.
- **MCP serverInfo version hardcoded "2.0.0"** (≠ package 2.4.0) in the server handshake.
- **#30** (Jinja extraction of `web_templates.py`, 2036-LOC string) still the "make it leaner" item; body references old `ai_history/` path.

## NOT committed (left for you)

- `docs/EXECUTION-PROMPT.md`, `docs/UMBAU.md` — real planning docs (Achse 1–4 + UX rebuild spec). Commit when ready: `git add docs/EXECUTION-PROMPT.md docs/UMBAU.md && git commit`.

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

- Default remote branch is **`master`**, not `main`.
- gunicorn is **not** in `.venv` (Docker image only); `lore-web` uses the Flask dev server locally.
- Test deps are **not** in pyproject (no `[dev]` extra) — fresh venvs need `pip install pytest pytest-cov coverage fastembed` by hand (follow-up to fix).
- Tailwind console warning ("cdn.tailwindcss.com should not be used in production") is the vendored dev build's banner — cosmetic.
- Subagent sessions have `project_path: None` in the index (cosmetic, affects project filter).
- Syncthing mirrors this repo to ai-workstation incl. `.git` — but **sync via git** (push/pull), don't rely on Syncthing for `.git` consistency.

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
   or a roadmap issue. Branch off master, never commit to master directly without CI.

---

<details><summary>Previous handoff — 2026-05-26 (rebrand + data foundation)</summary>

Product **Lore** (import package `lore`). Rebrand from `ai-history`, Forgejo deleted, data
re-synced to `~/.lore`, laptop-freeze fix (single-pass export + memory-capped systemd timer),
Claude subagent coverage 46→333, v2 store fixed (INSERT OR REPLACE), search v2-primary,
MIN_USER_PROMPTS=3. Axis-1 data-completeness (removed claude.py 500-char truncation, structured
tool_call outputs threaded by tool_use_id, skip-count tracking). See git history for detail.

</details>
