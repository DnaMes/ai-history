# Continue (fresh Claude Code session) — Lore #96/#103

Recommended: run `/clear`, then paste this into a clean session (cheaper +
sharper than a compacted context).

## Verify first
```
git branch --show-current   # fix/96-indexbuilder-streaming
git status                  # index.py, extraction.py, test_index_builder_streaming.py, design doc STAGED (uncommitted)
```
Read `HANDOFF.md` top section — it's the source of truth.

## Where we are
Bounding reload peak RSS. #96 done & pushed (PR #102 OPEN). **#103 warm-
incremental fix is STAGED, not committed.** Wins measured on real ~990-session
archive (peak VmHWM): cold 2084→1404, reload 2040→1421, warm incremental
2077→1429 MB. 1123 tests passed pre-commit.

## Do this next (in order)
1. **Resolve the open question**: does `messages_synced=0` appear on a **cold**
   `build_search_index(incremental=False)` too (check
   `SELECT COUNT(*) FROM sessions WHERE messages_synced=0` on the v2 db, and that
   those sessions still have message rows)? Background job `ba6nl49t3` was
   answering this — read its output or re-run. YES→benign, proceed. NO→bug in
   `add_reused_session`, investigate.
2. `git commit` the staged #103 changes; `git push github fix/96-indexbuilder-streaming`.
3. `.venv/bin/python -m pytest tests/ --no-cov -q` → expect 1123 passed, 1 skipped.
4. Update PR #102 body (#103 folded in). Confirm CI green.

## Guardrails / gotchas
- Steelman REJECTED mtime-diff v2 writes; the merged tagged-stream (`reused_ids`)
  approach was chosen to preserve DELETE-rebuild consistency. Don't reintroduce
  mtime-as-sole-reindex-trigger.
- Bug already fixed: `reused_ids or set()` drops the caller's live set — keep
  `if reused_ids is None`.
- Remote `github`; default `main`; `--no-cov` for ad-hoc pytest; measure RSS in a
  fresh process. #104 (opencode dedup ~425MB) still open as a separate follow-up.
