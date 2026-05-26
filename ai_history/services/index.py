"""Framework-free index reading, searching and deleted-session handling.

These are the pure (no Flask, no interface imports) entry points that
both the web interface and the MCP server consume. ``web_data`` wraps
them, passing its own — test-patchable — path globals.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

from .cache import threadsafe_lru_cache
from .extraction import build_search_index

logger = logging.getLogger(__name__)


# --- Deleted Session IDs ---


@threadsafe_lru_cache(maxsize=1)
def _load_deleted_session_ids_cached(path: str, mtime_ns: int, size: int) -> set[str]:
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if isinstance(payload, dict):
        values = payload.get("session_ids", [])
    else:
        values = payload
    return {str(value) for value in values if str(value).strip()}


def load_deleted_session_ids(deleted_sessions_path: Path) -> set[str]:
    """Load the set of tombstoned session ids from ``deleted_sessions_path``."""
    if not deleted_sessions_path.exists():
        return set()
    stat = deleted_sessions_path.stat()
    try:
        return set(
            _load_deleted_session_ids_cached(
                str(deleted_sessions_path), stat.st_mtime_ns, stat.st_size
            )
        )
    except Exception as exc:
        logger.warning("Failed to load deleted session ids from %s: %s", deleted_sessions_path, exc)
        return set()


def save_deleted_session_ids(
    session_ids: set[str], output_dir: Path, deleted_sessions_path: Path
) -> None:
    """Persist ``session_ids`` to ``deleted_sessions_path`` (owner-only, #41)."""
    from ai_history.utils.paths import restrict_file, secure_dir

    secure_dir(output_dir)
    with open(deleted_sessions_path, "w", encoding="utf-8") as handle:
        json.dump({"session_ids": sorted(session_ids)}, handle, indent=2)
    restrict_file(deleted_sessions_path)
    _load_deleted_session_ids_cached.cache_clear()


def remember_deleted_session_id(
    session_id: str, output_dir: Path, deleted_sessions_path: Path
) -> None:
    """Add ``session_id`` to the tombstone set and persist it."""
    ids = load_deleted_session_ids(deleted_sessions_path)
    ids.add(session_id)
    save_deleted_session_ids(ids, output_dir, deleted_sessions_path)


# --- Index Filtering ---


def apply_deleted_filter(payload: dict, deleted: set[str]) -> dict:
    """Drop tombstoned sessions from an index payload and recompute stats."""
    if not deleted:
        return payload

    sessions = [
        session for session in payload.get("sessions", []) if session.get("id") not in deleted
    ]

    by_tool: dict[str, int] = {}
    by_project: dict[str, int] = {}
    total_messages = 0
    for session in sessions:
        tool = str(session.get("tool") or "")
        if tool:
            by_tool[tool] = by_tool.get(tool, 0) + 1
        project = session.get("project")
        if project:
            by_project[project] = by_project.get(project, 0) + 1
        total_messages += int(session.get("messages") or 0)

    payload["sessions"] = sessions
    payload["stats"] = {
        "total_sessions": len(sessions),
        "total_messages": total_messages,
        "by_tool": by_tool,
        "by_project": by_project,
    }
    return payload


def apply_deleted_filter_to_results(results: list, deleted: set[str]) -> list:
    """Drop search results whose session id is tombstoned."""
    if not deleted:
        return results
    return [r for r in results if r.get("session", {}).get("id") not in deleted]


# --- Display Titles ---


def annotate_display_titles(sessions: list[dict]) -> list[dict]:
    """Add a ``display_title`` to each session, disambiguating duplicates."""
    title_counts: dict[str, int] = {}
    for session in sessions:
        raw_title = (session.get("title") or "").strip()
        if not raw_title:
            continue
        key = raw_title.casefold()
        title_counts[key] = title_counts.get(key, 0) + 1

    for session in sessions:
        raw_title = (session.get("title") or "").strip()
        session_id = str(session.get("id") or "")
        if raw_title:
            key = raw_title.casefold()
            if title_counts.get(key, 0) > 1:
                suffix = session_id[:8] if session_id else "session"
                session["display_title"] = f"{raw_title} · {suffix}"
            else:
                session["display_title"] = raw_title
        else:
            session["display_title"] = session_id[:12] if session_id else "Untitled Session"
    return sessions


# --- Cache Management ---


@threadsafe_lru_cache(maxsize=1)
def _load_index_cached(index_path: str, _mtime_ns: int, _size: int) -> dict:
    with open(index_path, "r", encoding="utf-8") as handle:
        return json.load(handle)


@threadsafe_lru_cache(maxsize=1)
def _load_index_v2_cached(db_path: str, _mtime_ns: int, _size: int) -> dict:
    """File-stat-keyed cache of the v2 store read (mirrors _load_index_cached)."""
    from ai_history.storage import load_index_v2

    return load_index_v2(Path(db_path).parent)


def clear_index_cache() -> None:
    """Clear the index-read caches owned by the service layer."""
    _load_index_cached.cache_clear()
    _load_index_v2_cached.cache_clear()
    _load_deleted_session_ids_cached.cache_clear()


# --- v2 store ---


def _v2_enabled() -> bool:
    """Whether to read sessions from the v2 SQLite store (issue #44).

    Default is **on**. Set ``AI_HISTORY_USE_V2=0`` (or false/no/off) to
    force the legacy index.json reader as an escape hatch.
    """
    raw = os.environ.get("AI_HISTORY_USE_V2", "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def _load_index_from_v2(index_path: Path, deleted: set[str]) -> Optional[dict]:
    """Load and post-process the index from the v2 store, or None to fall back.

    Returns the same dict shape as the JSON path (deleted-filtered, display
    titles annotated) or ``None`` when v2 is unavailable/unreadable.
    """
    if not _v2_enabled():
        return None
    try:
        from ai_history.storage import v2_is_available

        index_dir = index_path.parent
        # Staleness check: if a JSON index exists and is newer than the v2
        # store, the v2 store is stale — fall back to JSON (#36).
        if not v2_is_available(index_dir, compare_to=index_path):
            return None
        v2_db = index_dir / "index_v2.sqlite"
        stat = v2_db.stat()
        payload = _load_index_v2_cached(str(v2_db), stat.st_mtime_ns, stat.st_size)
    except Exception as exc:
        logger.warning("v2 index read failed, falling back to JSON: %s", exc)
        return None
    payload = apply_deleted_filter(payload, deleted)
    payload["sessions"] = annotate_display_titles(payload.get("sessions", []))
    return payload


# --- Index Loading ---


def load_index(
    index_path: Path,
    output_dir: Path,
    deleted: set[str],
) -> dict:
    """Load the search index, preferring the v2 store, building it if missing.

    ``deleted`` is the current tombstone set (callers pass
    ``load_deleted_session_ids(...)``).
    """
    v2_payload = _load_index_from_v2(index_path, deleted)
    if v2_payload is not None:
        return v2_payload

    if not index_path.exists():
        try:
            build_search_index(output_dir, index_path, deleted_ids=deleted)
        except Exception as exc:
            logger.warning("Failed to build index from extractors: %s", exc)
            return {"stats": {}, "sessions": []}
        # A rebuild also produces the v2 store — retry the v2 path once.
        v2_payload = _load_index_from_v2(index_path, deleted)
        if v2_payload is not None:
            return v2_payload
    if not index_path.exists():
        return {"stats": {}, "sessions": []}
    stat = index_path.stat()
    payload = _load_index_cached(str(index_path), stat.st_mtime_ns, stat.st_size)
    payload = apply_deleted_filter(payload, deleted)
    payload["sessions"] = annotate_display_titles(payload.get("sessions", []))
    return payload


def load_index_summary(index_path: Path, deleted: set[str]) -> dict:
    """Return lightweight index metadata without shipping full session records."""
    v2_payload = _load_index_from_v2(index_path, deleted)
    if v2_payload is not None:
        sessions = v2_payload.get("sessions", [])
        stats = v2_payload.get("stats", {})
        v2_db = index_path.parent / "index_v2.sqlite"
        return {
            "total_sessions": int(stats.get("total_sessions") or len(sessions)),
            "by_tool": dict(stats.get("by_tool") or {}),
            "last_updated": v2_payload.get("generated_at"),
            "index_size_bytes": v2_db.stat().st_size if v2_db.exists() else 0,
        }

    if not index_path.exists():
        return {
            "total_sessions": 0,
            "by_tool": {},
            "last_updated": None,
            "index_size_bytes": 0,
        }

    stat = index_path.stat()
    payload = _load_index_cached(str(index_path), stat.st_mtime_ns, stat.st_size)

    if deleted:
        sessions = [s for s in payload.get("sessions", []) if s.get("id") not in deleted]
        by_tool: dict[str, int] = {}
        for session in sessions:
            tool = str(session.get("tool") or "")
            if tool:
                by_tool[tool] = by_tool.get(tool, 0) + 1
        total_sessions = len(sessions)
    else:
        stats = payload.get("stats", {})
        by_tool = dict(stats.get("by_tool") or {})
        total_sessions = int(stats.get("total_sessions") or 0)

    return {
        "total_sessions": total_sessions,
        "by_tool": by_tool,
        "last_updated": payload.get("generated_at"),
        "index_size_bytes": stat.st_size,
    }


# --- Search ---


def search_index(
    index_path: Path,
    query: str,
    deleted: set[str],
    tool: Optional[str] = None,
    project: Optional[str] = None,
    limit: int = 50,
    scope: Optional[str] = None,
) -> list[dict]:
    """Search sessions, reading from whichever store ``load_index`` uses (#34).

    When the v2 store is the active source, search v2's FTS5 index so search
    results and the session list stay consistent. Otherwise fall back to the
    legacy SearchEngine over index.sqlite.

    ``scope`` optionally restricts matches to a message-role subset (#24):
    ``"user_only"``, ``"assistant_only"`` or ``"tool_results"``. Scoped
    search needs the v2 store's per-message rows — on the legacy fallback
    path scope is a no-op.

    Returns ``[{"session": <dict>, "score": <float>}]``.

    Raises:
        ValueError: when ``scope`` is not a recognised value.
    """
    index_dir = index_path.parent
    if _v2_enabled():
        try:
            from ai_history.storage import search_sessions, v2_is_available

            # Pass compare_to so a v2 store that is older than the JSON index
            # (e.g. a prune ran but the v2 dual-write failed with a constraint
            # error) is treated as stale and skipped — otherwise the legacy
            # JSON has 793 sessions and v2 has 0 and search silently returns
            # nothing.
            if v2_is_available(index_dir, compare_to=index_path):
                results = search_sessions(
                    index_dir, query, tool=tool, project=project, limit=limit, scope=scope
                )
                if results:
                    return apply_deleted_filter_to_results(results, deleted)
                # v2 returned nothing — fall through to legacy. Better to
                # double-check than to silently lie. Legacy may still have it.
        except ValueError:
            # Invalid scope — surface to the caller, do not fall back.
            raise
        except Exception as exc:
            logger.warning("v2 search failed, falling back to legacy: %s", exc)

    # Legacy SearchEngine has no per-message rows; validate scope but treat
    # any non-"all" value as a no-op (return the unfiltered legacy result).
    from ai_history.storage.search import SEARCH_SCOPES

    if (scope or "all").strip().lower() not in SEARCH_SCOPES:
        raise ValueError(
            f"Invalid scope '{scope}'. Expected one of: {', '.join(sorted(SEARCH_SCOPES))}."
        )

    from ai_history.search.engine import SearchEngine

    results = SearchEngine(index_path).search(query, tool=tool, project=project)[:limit]
    return apply_deleted_filter_to_results(results, deleted)
