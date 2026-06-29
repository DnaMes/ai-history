# HANDOFF — Lore — 2026-06-29 (QA + Issue triage)

> Continue on **ai-workstation** (`ssh ai-workstation`, VM 300 on pve-awow, tmux session `ai`).
> Update this before session ends.

## TL;DR — where things stand

Production-readiness QA done on the laptop. **Tests green (987 passed, 0 failed, coverage 83.84%).**
UI render quality is genuinely good now (Axis-2 paid off) — NOT "billig" anymore. Cross-tool
tool-cards render for both Claude and OpenCode. Four real bugs found during live QA, all filed
as GitHub issues with full execution prompts. Nothing blocking local/Docker use except the CLI
entry points (#66).

- **Version** 2.4.0 · **Repo** `~/projects/lab/ai/lore` · **GitHub** `DnaMes/lore` (default branch = `master`)
- **Data** `~/.lore` · **Docker** `lore-app` :5000 (`gunicorn --workers 1`)
- Live extractor counts (this machine): claude 424 · opencode 259 · vscode 79 · warp 61 · gemini 30 · cursor 27 · codex 25 · antigravity 0 · copilot 0 · aider absent

## Open issues filed THIS session (each has a paste-ready execution prompt in the body)

| # | Title | Sev | Branch suggested |
|---|---|---|---|
| [#66](https://github.com/DnaMes/lore/issues/66) | `lore-web` & `lore-mcp` CLI entry points dead (cli/web.py + cli/mcp.py are 0 bytes) | **P0 blocker** | `fix/cli-entry-points` |
| [#67](https://github.com/DnaMes/lore/issues/67) | `/api/stats/costs` all zeros — index carries no `tokens` field | P1 | `fix/cost-dashboard-zero` |
| [#68](https://github.com/DnaMes/lore/issues/68) | Claude command sessions leak `<local-command-caveat>` title + `[command:/exit]` noise | P1 | `fix/claude-command-noise` |
| [#69](https://github.com/DnaMes/lore/issues/69) | antigravity & copilot extractors say available=True but extract 0 | P2 | `fix/extractor-availability-truth` |

Recommended order: **#66 first** (small, unblocks non-Docker run), then #68 (user-visible noise),
then #67 (most-wanted feature shipping empty), then #69.

## Root causes (verified at code level — not symptoms)

- **#66** — `pyproject.toml` declares `lore-web="lore.cli.web:main"` / `lore-mcp="lore.cli.mcp:main_sync"` but both modules are empty → ImportError. Docker survives only because `Dockerfile:38` runs `gunicorn ... lore.interfaces.web:app` directly. `CLAUDE.md` documents them as working (stale). No clean local-run path exists (gunicorn is Docker-only; had to run `python -c "from lore.interfaces.web import app; app.run(...)"` for QA).
- **#67** — `_build_costs_payload()` (`web.py:1011`) reads `session.get("tokens")` from the flat index, which never persists that field (see comment at `web.py:1088`). Every session `continue`s. Fix is at the **index builder** layer (`lore/services/index.py`), not the route.
- **#68** — `strip_local_command_caveat_in_user_messages` exists (`web_services.py:9/157/251`) but the rule map (`web.py:263`) enables it for **opencode only**. Claude sessions skip it → caveat leaks into title + `[command:/exit]`/`[exit]`/`()` render as prompt cards. Keep nh3 two-pass XSS intact when fixing.
- **#69** — `is_available()` keys off dir presence, not real session data. `~/.antigravity` is an IDE install (mirror `vscode.py` globalStorage discovery to find chat path, or report unavailable). `~/.copilot` absent → wrong/old path.

## Done this session (committed + pushed)

- **`chore/gitignore-scratch` → master (ff-merge, commit 53cd488)**: gitignore `.coverage`, `.serena/`, `.obsidian-doc`, `MAINT-night-*.md`, `toc-verify.js`, `.playwright-mcp/`, session-continuation `.txt` dumps. Working dir is now clean.
- Filed #66–#69.

## NOT committed (left for you)

- `docs/EXECUTION-PROMPT.md`, `docs/UMBAU.md` — real planning docs (Achse 1–4 + UX rebuild spec). Commit when ready: `git add docs/EXECUTION-PROMPT.md docs/UMBAU.md && git commit`.

## Pre-existing open issues still relevant

- **#30** Jinja extraction (`web_templates.py` = 2036-LOC Python string) = the "make it leaner" item. Body still references old `ai_history/` path — update when worked.
- **#62** per-message token chips only with `?live=1` (related to #67, cross-linked).
- **#57** raw→imported gap (related to #69, cross-linked).
- #53 (render rebuild — largely done via #61/#64), #54, #55, #56, #33, #48, #29.

## How to run the web UI locally (until #66 is fixed)

```bash
cd ~/projects/lab/ai/lore
FLASK_SECRET_KEY=devtest .venv/bin/python -c \
  "from lore.interfaces.web import app; app.run(host='127.0.0.1', port=5057, threaded=True, use_reloader=False)"
# then: curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:5057/api/health  → 200
```
Or Docker: `docker compose up -d app` → :5000.

Live extractor probe (per-tool available + session count):
```bash
.venv/bin/python -c "
from lore.extractors import claude, codex, opencode, cursor, gemini, antigravity, vscode, warp
import inspect
for m in (claude,codex,opencode,cursor,gemini,antigravity,vscode,warp):
    c=[x for _,x in inspect.getmembers(m,inspect.isclass) if x.__module__==m.__name__ and x.__name__.endswith('Extractor')][0]()
    ok=c.is_available(); n=sum(1 for _ in c.extract_sessions()) if ok else '-'
    print(f'{m.__name__.split(chr(46))[-1]:12} available={ok} sessions={n}')
"
```

## Gotchas (still valid)

- Default remote branch is **`master`**, not `main`.
- gunicorn is **not** in `.venv` (Docker image only) — use Flask dev server locally.
- Tailwind console warning ("cdn.tailwindcss.com should not be used in production") is the vendored dev build's banner — cosmetic, ignore.
- Subagent sessions have `project_path: None` in the index (cosmetic, affects project filter).
- Syncthing mirrors this repo to ai-workstation incl. `.git` — but **sync via git** (push/pull), don't rely on Syncthing for `.git` consistency.

## Next session start

1. `ssh ai-workstation`, `tmux attach -t ai` (or new), `cd ~/projects/lab/ai/lore`.
2. `git fetch github && git checkout master && git pull` (get 53cd488 + this handoff).
3. `pip install -e . && .venv/bin/python -m pytest tests/` — confirm green baseline.
4. Start on **#66** (execution prompt is in the issue body).

---

<details><summary>Previous handoff — 2026-05-26 (rebrand + data foundation)</summary>

Product **Lore** (import package `lore`). Rebrand from `ai-history`, Forgejo deleted, data
re-synced to `~/.lore`, laptop-freeze fix (single-pass export + memory-capped systemd timer),
Claude subagent coverage 46→333, v2 store fixed (INSERT OR REPLACE), search v2-primary,
MIN_USER_PROMPTS=3. Axis-1 data-completeness (removed claude.py 500-char truncation, structured
tool_call outputs threaded by tool_use_id, skip-count tracking). See git history for detail.

</details>
