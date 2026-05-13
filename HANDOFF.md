# HANDOFF — ai-history — 2026-05-13

> Claude: update this before session ends with /compact or on Stop.

## Current Task

GitHub issues created — all 32 issues are live at https://github.com/DnaMes/ai-history/issues

## Decisions Made

- Fixed `tools/create_issues.sh` line 110: `"architecture""1d76db"` was missing a space between arguments, causing `$3` to be unbound under `set -euo pipefail`. One-char fix.
- CPU issue was Chrome (224% + 99% CPU), not the ai-history container. Container was at 6.78%.

## Files Changed

- `tools/create_issues.sh` — fixed missing space between label name and color args (line 110)

## All P0 Security Fixes (committed in previous sessions)

| Fix | Commit |
|-----|--------|
| Remove hardcoded Gemini OAuth creds | f88ecac |
| CSRF → SameSite=Strict + origin guard | a243ca5 |
| XSS in format_message_content | 5321aa9 |
| MCP error leak + atomic index writes + path traversal | d03d804 |

## GitHub Repo

Public repo: https://github.com/DnaMes/ai-history  
32 issues created covering: P0 (cleanup), P1 (security/perf), P2 (features), P3 (future)

## Blockers

None currently.

## Next Steps

Good candidates for next session (in priority order):

1. **#1b** — Rename `_new` suffix modules (`ai_history_mcp_new.py` → `ai_history/cli/mcp.py`)
2. **#1d** — Fix `safe_copy_db` temp file leak (30-min task, `utils/paths.py:64`)
3. **#1e** — Surface extractor exceptions in job metadata
4. **#15e** — Switch pre-commit to ruff (replace black+isort+flake8)
5. **#README** — Add screenshot + quickstart to README (important for public repo)
6. **#PyPI** — Publish to PyPI (needs CHANGELOG.md + author email in pyproject.toml)
