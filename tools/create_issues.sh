#!/usr/bin/env bash
# Create issues from docs/ROADMAP.md on Forgejo or GitHub.
#
# Usage:
#   tools/create_issues.sh forgejo                        # Forgejo (Tailscale only)
#   tools/create_issues.sh github DnaMes ai-history       # GitHub
#
# Requires:
#   - Forgejo: token at ~/.config/forgejo/token, network access to the host
#   - GitHub:  `gh auth status` working, repo exists (will not create the repo)

set -euo pipefail

HOST="${1:?usage: $0 (forgejo|github) [<owner> <repo>]}"
OWNER="${2:-}"
REPO="${3:-}"

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ROADMAP="$REPO_ROOT/docs/ROADMAP.md"

if [[ ! -f "$ROADMAP" ]]; then
    echo "ERROR: $ROADMAP not found" >&2
    exit 1
fi

# ---- helpers ----------------------------------------------------------------

create_issue_forgejo() {
    local title="$1"
    local body="$2"
    local labels_json="$3"  # JSON array string e.g. '["bug","p0"]'
    local token
    token="$(cat ~/.config/forgejo/token | tr -d '\n')"
    curl -fsS -X POST \
        "http://100.119.46.15:3000/api/v1/repos/erdna/ai-history/issues" \
        -H "Authorization: token $token" \
        -H "Content-Type: application/json" \
        -d "$(jq -n \
            --arg t "$title" --arg b "$body" --argjson l "$labels_json" \
            '{title: $t, body: $b, labels: $l}')"
    echo
}

create_issue_github() {
    local title="$1"
    local body="$2"
    local labels="$3"  # comma-separated list e.g. "bug,p0"
    gh issue create \
        --repo "$OWNER/$REPO" \
        --title "$title" \
        --body "$body" \
        --label "$labels"
}

# ---- ensure labels exist (GitHub only) -------------------------------------

if [[ "$HOST" == "github" ]]; then
    [[ -z "$OWNER" || -z "$REPO" ]] && { echo "github needs <owner> <repo>" >&2; exit 1; }
    for lbl in p0:E11D21 p1:F97316 p2:EAB308 p3:6B7280 \
               bug:D73A4A security:B60205 enhancement:0E8A16 \
               performance:5319E7 architecture:1D76DB docs:0075CA \
               tech-debt:FBCA04 extractor:7057FF qa:84B6EB; do
        name="${lbl%%:*}"; color="${lbl##*:}"
        gh label create "$name" --color "$color" --repo "$OWNER/$REPO" 2>/dev/null || true
    done
fi

# ---- issue definitions (id: title | labels | body) -------------------------

# A heredoc-fed list. Each row is: ID|TITLE|LABELS|BODY (BODY may contain \n).

issues=(
"1a|Drop unused Postgres + Redis stack from docker-compose|p0,security,architecture|docker-compose.yml exports DATABASE_URL/REDIS_URL and Dockerfile installs psycopg2-binary + redis, but the codebase stores everything in JSON+SQLite. Public-release blocker; contradicts the local-first claim.\n\n**Action**: delete the db/redis services from docker-compose.yml, remove psycopg2-binary and redis from Dockerfile, simplify compose to just the app container.\n\nFiles:\n- docker-compose.yml\n- Dockerfile:17"
"1b|Rename _new entry-point modules|p0,architecture|ai_history_mcp_new.py and ai_history_web_new.py are root-level legacy artifacts referenced by pyproject.toml:42-47. Embarrassing on PyPI.\n\n**Action**: move into the package as ai_history.cli.mcp and ai_history.cli.web. Update pyproject.toml scripts entries."
"1c|Make index.json writes atomic|p0,bug|web.py:369 and web.py:1156 open INDEX_PATH 'w' then json.dump. SIGINT mid-write corrupts the index.\n\n**Action**: write to a temp file in the same dir, then os.replace() atomically."
"1d|safe_copy_db leaks temp DB copies forever|p0,bug|utils/paths.py:64-92. Every reload leaves *.vscdb, *.sqlite, plus -wal/-shm in /tmp.\n\n**Action**: add try/finally cleanup or convert to a context manager."
"1e|Surface extractor exceptions to job results|p0,bug|web_data.py:213-217 and web.py:870-873 swallow extractor exceptions at logger.debug. A failing extractor disappears from sync results with no UI signal.\n\n**Action**: collect failures into job result metadata; show a per-tool status badge in the reload report."
"1f|MCP server leaks exception details to peer|p0,security|interfaces/mcp.py:209-211 catches bare Exception and embeds the message in the wire response. Leaks stack traces and file paths.\n\n**Action**: log details server-side, return generic 'Internal error'."
"2|Tool-call args bypass HTML sanitization (XSS)|p0,security,bug|web_formatting.py:177-178 re-injects unsanitized HTML AFTER bleach.clean. Tool-call args from untrusted JSONL/SQLite end up in raw markup.\n\n**Action**: run sanitize_rendered_html over the FINAL composed string (after placeholder substitution), or render tool blocks through bleach with details/summary in SANITIZE_TAGS."
"3|CSRF disabled on every state-changing API route|p0,security|@csrf.exempt on POST /api/reload-sessions, /api/cache/clear, /session/<id>/delete, /api/noise-rules/* (web.py:677, 699, 726, 1110, 1250, 1265). Behind a reverse proxy with cookies, a malicious page can trigger destructive actions.\n\n**Action**: remove @csrf.exempt or require X-Requested-With + reject non-JSON."
"4|Path traversal via poisoned export_path|p0,security|resolve_export_path (web_data.py:307-324) does not enforce containment under OUTPUT_DIR. A poisoned ~/.ai-history/index.json could trick GET /export/<id> into reading arbitrary files.\n\n**Action**: enforce resolved.is_relative_to(OUTPUT_DIR)."
"5|Container runs as root|p0,security|Dockerfile has no USER directive; bind-mounts read-only host secrets into /root/.\n\n**Action**: RUN useradd -m -u 10001 ai && USER ai. Mount under /home/ai/."
"6|Remove default Postgres password fallback|p0,security|docker-compose.yml resolves \${POSTGRES_PASSWORD:-changeme} to a known weak default. Once issue #1a lands this becomes moot, but if Postgres is kept for any reason, fail fast on missing env."
"7|Replace CSP unsafe-inline with nonces|p1,security|web.py:496-497. Inline scripts are static and small enough to hash."
"8|Only honor X-Forwarded-For when TRUSTED_PROXY is set|p1,security|web_utils.py:75-81 trusts the header verbatim. Bypasses rate limiter and can exhaust RATE_LIMIT_STATE memory."
"9|Refuse to start with ephemeral SECRET_KEY in production|p1,security|web.py:143 falls back to os.urandom(32).hex(). Sessions/CSRF tokens invalidate on every restart.\n\n**Action**: log warning on missing FLASK_SECRET_KEY; refuse to start when FLASK_ENV=production."
"10|Add pip-audit + bandit to CI|p1,security,qa|.github/workflows/ci.yml has bandit (linter only). Add pip-audit and run on push/PR. Required for OSS supply-chain hygiene."
"11|Generate requirements.lock|p1,security|pip-compile from pyproject.toml; commit the lockfile. Pins transitive deps and gives reproducible builds."
"12|Add SRI hashes to CDN script tags or self-host|p1,security|web_templates.py:18-19 loads tailwind + highlight.js without integrity=. CDN compromise = stored XSS.\n\nDuplicate of #19."
"13|Drop data: from img-src CSP|p1,security|web.py:498. Combined with #2 enables SVG-based payloads."
"14|Remove dead Docker deps psycopg2-binary and redis|p0,tech-debt|See #1a."
"15|Tighten validate_session_id|p1,security|utils/security.py:226-241 allows :, *, ?, spaces, and length 256. Tighten to [A-Za-z0-9_.\\-]{1,128}."
"16|Incremental index sync|p1,performance|web_data.py:177 → exporters/index.py:289 wipe + bulk-INSERT every reload. At 1672 sessions: ~12 KB JSON × 1672 = 19 MB written, plus FTS rebuild.\n\n**Action**: stat-mtime each source file, INSERT OR REPLACE only changed sessions. Reload time drops from O(all) to O(changed)."
"17|Strip search_text/keywords from dashboard payload|p1,performance|load_index() at web_data.py:256 returns the entire 19 MB blob; the dashboard never reads search_text or keywords. Split into index_meta.json (cards) and index_search.json (only on /search). Expected 75% reduction."
"18|FTS5 with content=sessions external content table|p1,performance|search/engine.py:71. The 78 MB SQLite is half wasted because search_text is duplicated between sessions and sessions_fts.\n\n**Action**: switch to FTS5 external content; halves SQLite size, speeds cold cache."
"19|Vendor Tailwind + highlight.js|p1,performance,security|Drop CDN runtime dependency. Use Tailwind CLI prebuild → ship static/app.css. Pin highlight.js with SRI hash. Restores air-gapped/offline use as documented in AGENTS.md:149."
"20|Streamed indexing for huge sessions|p2,performance|claude.py accumulates all messages in RAM; IndexBuilder only uses messages[:30]. Add a short-circuit indexing path that yields metadata + first N messages.\n\nFor 15K-message sessions: 10-50× memory reduction."
"21|Stop re-exporting from web.py|p2,architecture,tech-debt|The _TEST_EXPORTS shim and the CLAUDE.md monkeypatch table both hint at leaky modularization. Delete the re-exports, fix the ~6 dependent tests, retire the patch table."
"22|Merge web_helpers.py into web_services.py|p2,architecture|Six sibling modules is one too many."
"23|Hoist _build_search_text/_infer_title out of dual loops|p2,performance|exporters/index.py:316-319 runs each twice (JSON + SQLite). Compute once, write twice."
"24|Mtime-keyed cache for load_sessions_for_tool|p2,performance|web_data.py:228 — currently invalidated only on process restart. Mirror the _load_index_cached pattern."
"25|web_jobs.py should own _audit_* helpers|p2,architecture|Currently web.py defines them and web_jobs.py reaches back via late imports. Inverted dependency."
"25a|Decompose session_detail (199 LOC, cyclomatic ~25)|p2,architecture|web.py:908-1106 mixes controller + 5 nested closures + an OpenCode-specific fallback. Split into controller + renderer."
"25b|Decompose mcp.create_server() (445 LOC)|p2,architecture|interfaces/mcp.py:214 defines every tool inline. Move each tool to its own function or sub-module."
"25c|Move HTML out of web_templates.py|p2,architecture,tech-debt|2,036 LOC of HTML/JS/CSS in Python strings. The template_folder= arg in web.py:142 is set but unused. Move to ai_history/templates/*.html and load via FileSystemLoader. Enables editor syntax highlighting + a11y linting."
"25d|Build Jinja2 Environment once at module import|p2,performance|web.py:412-418 creates a new env on every render() call, defeating template caching."
"25e|Common SQLite-DB iteration helper in BaseExtractor|p2,architecture|Pattern duplicated in warp.py, cursor.py, vscode.py, opencode.py. Hoist to BaseExtractor.iter_sqlite_dbs()."
"25f|Centralize tool data root paths|p2,architecture|Path.home() / '.cursor' / ... etc. repeated ~25 times across extractors. Move to utils/paths.tool_data_root('opencode')."
"26|Parametrized contract test across all 11 extractors|p1,qa|@pytest.mark.parametrize('extractor_cls', ALL_EXTRACTORS) asserting Tool/Role enums, is_available(), iterator type. Today only Claude/Gemini/Codex are checked."
"27|Add tests for antigravity, copilot, cursor, vscode extractors|p1,qa|Currently zero direct coverage."
"28|Public /api/v1/* route contract tests|p1,qa|Locks the OSS API surface before users depend on it. Untested: /api/v1/search, /api/v1/sessions/*, /api/v1/threads/*, /api/v1/messages/*."
"29|Add pytest-cov + 80% coverage gate|p2,qa|Publish HTML artifact in CI."
"30|Smoke test booting Flask + hitting /api/health|p2,qa|Boot gunicorn in CI, hit /api/health, /api/ready, /api/build-info. Catches deployment regressions."
"31|Schema snapshot test for index.json|p2,qa|Golden file to catch silent format breaks."
"32|Property-based parser tests with hypothesis|p2,qa|Feed malformed JSONL/JSON to each _parse_session*. Must not raise uncaught."
"33|Add pytest-randomly|p3,qa|Expose order-dependence in tests touching ~/.ai-history/."
"34|Token cost dashboard|p1,enhancement|Per tool / project / over time. Headline missing feature; claude-code-history-viewer ships it. ~1 week effort, high impact."
"35|Semantic search via local embeddings|p2,enhancement|sqlite-vec + nomic-embed-text via Ollama. Zero competitors have shipped this. 'Find sessions where I debugged auth middleware' — queries FTS misses."
"36|Shareable static HTML export|p1,enhancement|Single self-contained file per session, zero deps, works via email/file share. SpecStory does this with cloud links — we do it offline-first."
"37|Headline ai-history rules in README|p1,docs,enhancement|Auto-generate .cursorrules / CLAUDE.md from history. SpecStory's primary differentiator. Existing 'ai-history rules' command needs polish + UI exposure."
"38|Session timeline / git-diff view|p2,enhancement|Show file changes alongside conversation. Massive value for code review and audit; nobody has shipped this."
"39|Project-level cost attribution|p2,enhancement|Pairs with #34. Lets developers bill clients or justify AI spend."
"40|Noise filter UI|p2,enhancement|NOISE_RULES_PATH exists; expose as drag-and-drop web UI with live preview."
"41|MCP-over-HTTP server mode|p2,enhancement|Add --transport streamable-http so Cursor and other MCP hosts can query history."
"42|Verify and deepen Warp Block import|p2,enhancement,extractor|Confirm Warp coverage matches spec; add block-level extraction."
"43|ai-history digest weekly summary|p3,enhancement|Sessions, cost, top projects. Habit-forming; trivial."
"44|v3: single SQLite source of truth|p3,architecture|Drop index.json. Sessions/stats live only in SQLite. Eliminates JSON↔SQLite double write."
"45|v3: persistent JobStore (multi-worker safe)|p3,architecture|RELOAD_JOBS in-memory dict forces gunicorn --workers 1. Add SQLiteJobStore (default) and RedisJobStore (opt-in)."
"46|v3: Jinja templates on disk + Tailwind CLI prebuild|p3,architecture|See #25c."
"47|v3: optional FastAPI alongside Flask|p3,architecture|Reuse services layer, expose typed OpenAPI for the public v1 API."
"48|v3: plugin extractor SDK|p3,architecture,enhancement|pip install ai-history-extractor-foo style. Stable plugin API + cookiecutter template."
"49|README: lead with 'your AI sessions ARE documentation'|p2,docs|SpecStory's framing. Reposition the README around rule generation and digest."
"50|README: comparison table vs claude-code-history-viewer / claude-history / specstory|p2,docs|Highlight the multi-tool moat (no other OSS tool covers 9+ AI assistants)."
)

echo "Creating ${#issues[@]} issues on $HOST..."
for line in "${issues[@]}"; do
    IFS='|' read -r id title labels body <<< "$line"
    body_processed="$(printf '%b' "$body")"
    full_title="[$id] $title"
    if [[ "$HOST" == "forgejo" ]]; then
        labels_json="$(echo "[\"$labels\"]" | sed 's/,/","/g')"
        create_issue_forgejo "$full_title" "$body_processed" "$labels_json"
    else
        create_issue_github "$full_title" "$body_processed" "$labels"
    fi
    sleep 0.3
done

echo "Done."
