# HANDOFF — Lore — 2026-06-29 (QA + 4 issues + 3 follow-ups, all merged)

> Continue on **ai-workstation** (`ssh ai-workstation`, VM 300 on pve-awow, tmux session `ai`).
> ✅ Workstation synced to latest master (b9b3dc4). venv built, tests green, HTTPS+gh remote.
> Update this before session ends.

## TL;DR — all 4 QA bugs + 3 follow-ups shipped, master clean

Production-readiness QA + full fix pass done autonomously. UI render quality is genuinely good
(Axis-2 paid off) — NOT "billig". Seven PRs (#70–#75 + docs), each CI-green (lint + bandit +
pip-audit + tests 3.11/3.12), squash-merged to master. **Suite 1004 passed, coverage ~83.9%.**

| # | Fix | PR | Status |
|---|---|---|---|
| [#66](https://github.com/DnaMes/lore/issues/66) | `lore-web`/`lore-mcp` CLI entry points (were 0-byte modules) | [#70](https://github.com/DnaMes/lore/pull/70) | ✅ closed |
| [#68](https://github.com/DnaMes/lore/issues/68) | Strip `<local-command-caveat>` title leak + `[command:/exit]` render noise | [#71](https://github.com/DnaMes/lore/pull/71) | ✅ closed |
| [#67](https://github.com/DnaMes/lore/issues/67) | Cost dashboard: persist per-session token total (migration 11 + all layers) | [#72](https://github.com/DnaMes/lore/pull/72) | ✅ closed |
| [#69](https://github.com/DnaMes/lore/issues/69) | antigravity/copilot drops surfaced as skip reasons (not silent 0) | [#73](https://github.com/DnaMes/lore/pull/73) | ✅ closed |
| — | `[dev]` extra in pyproject + MCP serverInfo version → `lore.__version__` | [#74](https://github.com/DnaMes/lore/pull/74) | ✅ merged |
| — | Cost dashboard: `untokened_count` (sessions without token data, not dropped) | [#75](https://github.com/DnaMes/lore/pull/75) | ✅ merged |

- **Version** 2.4.0 · **Repo** `~/projects/lab/ai/lore` · **GitHub** `DnaMes/lore` (default `master`, HEAD **b9b3dc4**)
- **Data** `~/.lore` · **Docker** `lore-app` :5000 (`gunicorn --workers 1`)
- `lore-web --port 5057` works locally; `pip install -e ".[dev]"` sets up the full dev env.
- Cost dashboard real: `/api/stats/costs` → 5.57B tokens / 719 tokened + 191 untokened sessions.
- Planning docs (`docs/EXECUTION-PROMPT.md`, `docs/UMBAU.md`) are now committed (were churning untracked).

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
