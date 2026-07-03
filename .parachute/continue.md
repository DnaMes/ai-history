# Continue — Lore #96/#103 IndexBuilder RAM (any agent)

## Verify state before trusting this document
The repo may have moved on. FIRST run:
```
git branch --show-current   # expect: fix/96-indexbuilder-streaming
git status                  # expect staged: index.py, extraction.py, test_index_builder_streaming.py, design doc
git log --oneline -3
```
Then read `HANDOFF.md` (source of truth) top section.

## Context
Bounding reload peak RSS in Lore (AI-session history tool). Branch
`fix/96-indexbuilder-streaming`, PR **#102 OPEN**. #96 (streaming build_index +
25MB VSCode file cap) already committed & pushed. **#103 (warm-incremental
memory) is STAGED but NOT committed.**

Measured wins (peak VmHWM, real archive): cold 2084→1404, reload 2040→1421,
warm incremental 2077→1429 MB. 1123 tests passed before the pending commit.

## Immediate next step
1. Read background job `ba6nl49t3` output
   (`/tmp/claude-1000/-home-dnames-projects-lab-ai-lore/2bcc8574-b5af-433f-af88-1e9b51b8f7f6/../tasks/ba6nl49t3.output`
   — or just re-run: cold `build_search_index(incremental=False)`, then
   `SELECT COUNT(*) FROM sessions WHERE messages_synced=0` on the v2 db).
   **Question: does messages_synced=0 appear on a COLD build too?**
   - YES + those sessions still have message rows → pre-existing/benign → proceed.
   - NO (only after #103's incremental) → BUG in `add_reused_session` routing;
     investigate before committing.
2. If benign: `git commit` the staged changes (see HANDOFF "Next steps" for
   message intent), `git push github fix/96-indexbuilder-streaming`.
3. Re-run: `.venv/bin/python -m pytest tests/ --no-cov -q` (expect 1123 passed).
4. Update PR #102 body: #103 folded in, warm incremental now 1429 MB.

## Key facts
- Remote is `github` (not origin). Default branch `main`. venv Python 3.12 at `.venv/`.
- Coverage is in pytest addopts → pass `--no-cov` for ad-hoc runs.
- RSS harness: `/tmp/claude-1000/.../scratchpad/measure_rss.py` (may be gone; recreate:
  drain extractors into build_index, read `/proc/self/status` VmHWM). Measure
  incremental in a FRESH process (HWM is process-wide).
- The aliasing bug already fixed: never `reused_ids or set()` (drops live set).
