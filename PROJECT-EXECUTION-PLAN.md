# AI-History Execution Plan (Agents + Subagents)

This plan is optimized for autonomous execution with your agent stack.

## Goals

- Deliver a reliable local-first session/chat database across tools.
- Match a SpecStory-like browsing and session-review experience.
- Keep ingestion manual/on-click (`sync`/`export`), no live pull requirement.

## Current Status

Completed in this pass:

- Fixed index consistency in `sync` (no partial-index overwrite).
- Added centralized tool alias mapping used across CLI/MCP/session switching.
- Fixed MCP tool switching alias mismatch (`gemini` vs `gemini-cli`).
- Hardened timestamp fallback to epoch instead of `now()`.
- Updated web CSP to allow currently used CDN/font assets.
- Added unique markdown export filenames to avoid collisions.
- Added initial tests for aliasing, datetime fallback, export filename uniqueness.
- Added deterministic web security probe-matrix tests for route/status hardening.
- Fixed unknown thread detail handling to return `404` (instead of rendering empty `200`).
- Live app-level verification remains blocked by Traefik Basic auth (`401`) on deployed URL.
- Added reusable `ai-history-web-probe` CLI for local/live route+API probe matrix checks with explicit gateway-auth blocked detection.
- Executed `ai-history-web-probe` against deployed URL and confirmed deterministic BLOCKED state until credentials are supplied.
- Using known Basic auth credentials from existing E2E script, live parity currently fails on: unknown thread (`200` vs expected `404`), search validation for `q=ok;drop` (`200` vs `400`), search validation for `project=bad;project` (`200` vs `400`), and intermittent timeout on unknown export probe.
- Hardened `/export/<session_id>` unknown-id behavior to return `404` without extractor fallback scans by default (`AI_HISTORY_EXPORT_FALLBACK_SCAN=true` re-enables legacy fallback), improving deterministic probe behavior and avoiding timeout-prone scans.
- Added `/api/build-info` runtime metadata endpoint + `X-AI-History-Revision` response header and integrated build-info capture into `ai-history-web-probe` output to make deployed/runtime drift explicitly observable during parity verification.

## Workstreams

### WS1 - Core Reliability (P0)

#### Issue 1: Index consistency guardrails

- **Priority:** P0
- **Owner Agent:** `/impl`
- **Subagent:** `/a` (review)
- **Tasks:**
  - Add regression tests for `sync` sequence (`sync tool A`, `sync tool B`, ensure no index shrink).
  - Add explicit comment and unit around index merge behavior.
- **DoD:** index session count never drops unless prune is invoked.

#### Issue 2: Alias consistency end-to-end

- **Priority:** P0
- **Owner Agent:** `/impl`
- **Subagent:** `/e` (call-site discovery)
- **Tasks:**
  - Ensure all user-facing tool filters accept aliases.
  - Ensure all internal storage uses canonical tool names.
- **DoD:** aliases work in CLI, MCP, Web API, session switching.

#### Issue 3: Timestamp safety policy

- **Priority:** P0
- **Owner Agent:** `/debug`
- **Subagent:** `/a`
- **Tasks:**
  - Add malformed timestamp fixtures per extractor.
  - Verify sort order remains stable and deterministic.
- **DoD:** no silent `now()` fallback in parse failures.

### WS2 - Product Hardening (P1)

#### Issue 4: Web modularization

- **Priority:** P1
- **Owner Agent:** `/bulk`
- **Subagent:** `/a`
- **Tasks:**
  - Split `ai_history/interfaces/web.py` into route modules + render/services.
  - Keep behavior parity and route compatibility.
- **DoD:** same endpoints, lower file complexity, easier testing.

#### Issue 5: Extractor contract tests

- **Priority:** P1
- **Owner Agent:** `/impl`
- **Subagent:** `/e`
- **Tasks:**
  - Add fixture-driven tests for each extractor (happy + malformed).
  - Validate role mapping, timestamps, message assembly.
- **DoD:** every extractor covered by at least 2 tests.

#### Issue 6: Search parity tests (JSON + SQLite)

- **Priority:** P1
- **Owner Agent:** `/impl`
- **Subagent:** `/a`
- **Tasks:**
  - Verify top-N behavior is reasonable in both search paths.
  - Validate tool/project filters with aliases.
- **DoD:** deterministic filter behavior with canonicalized tools.

### WS3 - Release Readiness (P1/P2)

#### Issue 7: Logging cleanup

- **Priority:** P1
- **Owner Agent:** `/bulk`
- **Tasks:**
  - Replace debug `print` in web session route with logger calls.
  - Add env-driven debug level toggle.
- **DoD:** clean CLI/web output in normal mode.

#### Issue 8: GitHub release docs

- **Priority:** P1
- **Owner Agent:** `/doc`
- **Tasks:**
  - Add `CONTRIBUTING.md`.
  - Add "Known limitations" and roadmap to `README.md`.
  - Add architecture diagram section.
- **DoD:** first-time contributors can run and validate quickly.

#### Issue 9: SpecStory polish pass

- **Priority:** P2
- **Owner Agent:** `/ui`
- **Subagent:** `/a`
- **Tasks:**
  - Tighten TOC behavior and message pair rendering.
  - Improve thread detail UX and code block controls.
- **DoD:** cleaner, more intentional session reading flow.

## Suggested Sprint Order

### Sprint A (1-2 days)

- WS1 Issues 1-3

### Sprint B (2-3 days)

- WS2 Issues 4-6

### Sprint C (1-2 days)

- WS3 Issues 7-9

## Validation Checklist

- `python3 ai_history_cli.py check`
- `python3 ai_history_cli.py list --tool gemini --limit 5`
- `python3 ai_history_cli.py --output-dir /tmp/ai-history-e2e sync gemini`
- `python3 ai_history_cli.py --output-dir /tmp/ai-history-e2e sync codex`
- Verify `/tmp/ai-history-e2e/index.json` session count does not shrink.

## Notes for Agent Orchestration

- Use `/e` first for impact mapping before bulk refactors.
- Keep commits small and scoped by issue.
- Prefer fixture-based tests over live home-directory dependencies.
- Keep canonical tool names in storage/index; normalize at input boundaries.
