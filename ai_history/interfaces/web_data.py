"""Data loading and caching for the web interface.

This module handles session loading, index management, and data caching
for the web interface.
"""

import json
import logging
import os
import re
import threading
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Optional

from ai_history.core.models import Role, Tool, UnifiedMessage, UnifiedSession
from ai_history.exporters.index import IndexBuilder, _stat_mtime_ns
from ai_history.extractors.factory import get_all_extractors
from ai_history.titles.generator import TitleGenerator, TitleStrategy

from .web_utils import ActionJobCancelledError

logger = logging.getLogger(__name__)

# Thread-safe LRU cache wrapper
_threadsafe_cache_locks: dict = {}
_threadsafe_cache_lock = threading.Lock()


def threadsafe_lru_cache(maxsize: int = 128) -> Callable:
    """Thread-safe LRU cache decorator for use in multi-threaded Flask applications."""

    def decorator(func: Callable) -> Any:
        cached_func = lru_cache(maxsize=maxsize)(func)
        cache_lock = threading.Lock()

        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with cache_lock:
                return cached_func(*args, **kwargs)

        wrapper.cache_clear = cached_func.cache_clear  # type: ignore[attr-defined]
        wrapper.cache_info = cached_func.cache_info  # type: ignore[attr-defined]
        return wrapper

    return decorator


# Paths
OUTPUT_DIR = Path.home() / ".ai-history"
INDEX_PATH = OUTPUT_DIR / "index.json"
DELETED_SESSIONS_PATH = OUTPUT_DIR / "deleted_sessions.json"

# Clear OpenCode cache if requested
if os.environ.get("AI_HISTORY_CLEAR_OPENCODE_CACHE", "").lower() == "true":
    opencode_state_cache = OUTPUT_DIR / "cache" / "opencode_state.json"
    if opencode_state_cache.exists():
        opencode_state_cache.unlink()


# --- Deleted Session IDs ---


@threadsafe_lru_cache(maxsize=1)
def _load_deleted_session_ids_cached(path: str, mtime_ns: int, size: int):
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if isinstance(payload, dict):
        values = payload.get("session_ids", [])
    else:
        values = payload
    return {str(value) for value in values if str(value).strip()}


def load_deleted_session_ids() -> set[str]:
    if not DELETED_SESSIONS_PATH.exists():
        return set()
    stat = DELETED_SESSIONS_PATH.stat()
    try:
        return set(
            _load_deleted_session_ids_cached(
                str(DELETED_SESSIONS_PATH), stat.st_mtime_ns, stat.st_size
            )
        )
    except Exception as exc:
        logger.warning("Failed to load deleted session ids from %s: %s", DELETED_SESSIONS_PATH, exc)
        return set()


def _save_deleted_session_ids(session_ids: set[str]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(DELETED_SESSIONS_PATH, "w", encoding="utf-8") as handle:
        json.dump({"session_ids": sorted(session_ids)}, handle, indent=2)
    _load_deleted_session_ids_cached.cache_clear()


def remember_deleted_session_id(session_id: str) -> None:
    ids = load_deleted_session_ids()
    ids.add(session_id)
    _save_deleted_session_ids(ids)


# --- URL Sanitization ---


def _sanitize_next_url(next_url: str) -> str:
    from urllib.parse import urlparse

    value = (next_url or "").strip()
    if not value:
        return ""
    parsed = urlparse(value)
    if parsed.scheme or parsed.netloc:
        return ""
    if not value.startswith("/") or value.startswith("//"):
        return ""
    return value


# --- Index Filtering ---


def _apply_deleted_filter(payload: dict) -> dict:
    deleted = load_deleted_session_ids()
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


# --- Cache Management ---


def clear_index_cache():
    _load_index_cached.cache_clear()
    _load_index_v2_cached.cache_clear()
    _load_deleted_session_ids_cached.cache_clear()
    load_export_lookup.cache_clear()


def clear_sessions_cache():
    load_sessions_for_tool.cache_clear()


# --- Index Building ---


def _build_index_from_extractors(
    tool_filter: Optional[str] = None,
    progress_callback=None,
    should_stop=None,
    incremental: bool = True,
):
    """Build the search index.

    When ``incremental=True`` (default) sessions already present in the
    existing index whose source-file mtime hasn't changed are reused verbatim
    instead of being re-processed by :class:`IndexBuilder`. Set
    ``incremental=False`` to force a full rebuild.
    """
    extractors = get_all_extractors()
    selected = [
        extractor
        for extractor in extractors
        if extractor.is_available() and (not tool_filter or extractor.tool.value == tool_filter)
    ]

    existing_by_id: dict[str, dict] = {}
    if incremental and INDEX_PATH.exists():
        try:
            with open(INDEX_PATH, "r", encoding="utf-8") as handle:
                existing_payload = json.load(handle)
            for entry in existing_payload.get("sessions", []) or []:
                sid = str(entry.get("id") or "")
                if sid:
                    existing_by_id[sid] = entry
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Failed to read existing index for incremental build: %s", exc)

    sessions = []
    reused_entries: list[dict] = []
    # The full UnifiedSession objects behind reused_entries — incremental sync
    # has already extracted them (messages included), so we hand them to the
    # v2 store as complete sessions instead of metadata-only rows (#35).
    reused_sessions = []
    reused_ids: set[str] = set()
    errors: list[dict] = []
    title_generator = TitleGenerator(strategy=TitleStrategy.FAST)
    total = len(selected) or 1

    for i, extractor in enumerate(selected, start=1):
        if should_stop and should_stop():
            raise ActionJobCancelledError("Cancelled by user")
        if progress_callback:
            progress_callback(15 + int((i - 1) / total * 45), f"Loading {extractor.tool.value}")
        try:
            extracted_sessions = []
            for session in extractor.extract_sessions():
                if should_stop and should_stop():
                    raise ActionJobCancelledError("Cancelled by user")

                if incremental:
                    prior = existing_by_id.get(session.session_id)
                    if prior is not None:
                        prior_mtime = prior.get("source_mtime")
                        current_mtime = _stat_mtime_ns(session.source_path)
                        if (
                            prior_mtime is not None
                            and current_mtime is not None
                            and prior_mtime == current_mtime
                            and session.session_id not in reused_ids
                        ):
                            reused_entries.append(prior)
                            # Keep the fully-extracted session for the v2 store
                            # so its message rows are written too (#35).
                            reused_sessions.append(session)
                            reused_ids.add(session.session_id)
                            continue

                title = title_generator.generate(session, force=False)
                if title:
                    session.title = title
                extracted_sessions.append(session)
            sessions.extend(extracted_sessions)
        except ActionJobCancelledError:
            raise
        except Exception as exc:
            logger.warning(
                "Extractor %s failed during index build: %s",
                extractor.tool.value,
                exc,
                exc_info=True,
            )
            errors.append({"extractor": extractor.tool.value, "error": str(exc)})
            continue

    deleted = load_deleted_session_ids()
    filtered = [session for session in sessions if session.session_id not in deleted]
    reused_filtered = [entry for entry in reused_entries if entry.get("id") not in deleted]
    reused_sessions_filtered = [
        s for s in reused_sessions if s.session_id not in deleted
    ]
    IndexBuilder(OUTPUT_DIR).build_index(
        filtered,
        {},
        reused_entries=reused_filtered if reused_filtered else None,
        reused_sessions=reused_sessions_filtered if reused_sessions_filtered else None,
    )

    if progress_callback:
        message = (
            f"Index written ({len(reused_filtered)} reused, {len(filtered)} refreshed)"
            if incremental
            else "Index written"
        )
        progress_callback(62, message)

    return errors


@threadsafe_lru_cache(maxsize=128)
def load_sessions_for_tool(tool: Optional[str] = None):
    extractors = get_all_extractors()
    sessions = []
    title_generator = TitleGenerator(strategy=TitleStrategy.FAST)

    for extractor in extractors:
        if tool and extractor.tool.value != tool:
            continue
        if not extractor.is_available():
            continue
        try:
            extracted_sessions = list(extractor.extract_sessions())
            for session in extracted_sessions:
                title = title_generator.generate(session, force=False)
                if title:
                    session.title = title
            sessions.extend(extracted_sessions)
        except Exception as exc:
            logger.debug("Failed loading sessions for tool %s: %s", tool, exc)
            continue
    deleted = load_deleted_session_ids()
    if deleted:
        sessions = [session for session in sessions if session.session_id not in deleted]
    return sessions


def _v2_enabled() -> bool:
    """Whether to read sessions from the v2 SQLite store (issue #44).

    Default is **off** while the v2 migration is hardened (issues #34/#35/#36).
    Set ``AI_HISTORY_USE_V2=1`` (or true/yes/on) to opt in. The default flips
    back to on once the v2 store is proven consistent and crash-safe.
    """
    raw = os.environ.get("AI_HISTORY_USE_V2", "0").strip().lower()
    return raw in ("1", "true", "yes", "on")


def _load_index_from_v2():
    """Load and post-process the index from the v2 store, or None to fall back.

    Returns the same dict shape as the JSON path (deleted-filtered, display
    titles annotated) or ``None`` when v2 is unavailable/unreadable so the
    caller can fall back to index.json.

    The v2 DB is located relative to ``INDEX_PATH`` (not OUTPUT_DIR) so it
    follows the same directory the JSON reader uses — keeping the two paths
    consistent and letting tests that patch INDEX_PATH stay isolated.
    """
    if not _v2_enabled():
        return None
    try:
        from ai_history.storage import v2_is_available

        index_dir = INDEX_PATH.parent
        if not v2_is_available(index_dir):
            return None
        v2_db = index_dir / "index_v2.sqlite"
        stat = v2_db.stat()
        payload = _load_index_v2_cached(str(v2_db), stat.st_mtime_ns, stat.st_size)
    except Exception as exc:
        logger.warning("v2 index read failed, falling back to JSON: %s", exc)
        return None
    payload = _apply_deleted_filter(payload)
    payload["sessions"] = _annotate_display_titles(payload.get("sessions", []))
    return payload


@threadsafe_lru_cache(maxsize=1)
def _load_index_v2_cached(db_path: str, _mtime_ns: int, _size: int):
    """File-stat-keyed cache of the v2 store read (mirrors _load_index_cached)."""
    from ai_history.storage import load_index_v2

    return load_index_v2(Path(db_path).parent)


def search_index(query, tool=None, project=None, limit=50):
    """Search sessions, reading from whichever store load_index() uses (#34).

    When the v2 store is the active source, search v2's FTS5 index so search
    results and the session list stay consistent. Otherwise fall back to the
    legacy SearchEngine over index.sqlite.

    Returns ``[{"session": <dict>, "score": <float>}]``.
    """
    index_dir = INDEX_PATH.parent
    if _v2_enabled():
        try:
            from ai_history.storage import search_sessions, v2_is_available

            if v2_is_available(index_dir):
                results = search_sessions(
                    index_dir, query, tool=tool, project=project, limit=limit
                )
                return _apply_deleted_filter_to_results(results)
        except Exception as exc:
            logger.warning("v2 search failed, falling back to legacy: %s", exc)

    from ai_history.search.engine import SearchEngine

    results = SearchEngine(INDEX_PATH).search(query, tool=tool, project=project)[:limit]
    return _apply_deleted_filter_to_results(results)


def _apply_deleted_filter_to_results(results):
    """Drop search results whose session id is tombstoned."""
    deleted = load_deleted_session_ids()
    if not deleted:
        return results
    return [r for r in results if r.get("session", {}).get("id") not in deleted]


def load_index():
    # Prefer the v2 SQLite store; fall back to index.json transparently.
    v2_payload = _load_index_from_v2()
    if v2_payload is not None:
        return v2_payload

    if not INDEX_PATH.exists():
        try:
            _build_index_from_extractors()
        except Exception as exc:
            logger.warning("Failed to build index from extractors: %s", exc)
            return {"stats": {}, "sessions": []}
        # A rebuild also produces the v2 store — retry the v2 path once.
        v2_payload = _load_index_from_v2()
        if v2_payload is not None:
            return v2_payload
    if not INDEX_PATH.exists():
        return {"stats": {}, "sessions": []}
    stat = INDEX_PATH.stat()
    payload = _load_index_cached(str(INDEX_PATH), stat.st_mtime_ns, stat.st_size)
    payload = _apply_deleted_filter(payload)
    payload["sessions"] = _annotate_display_titles(payload.get("sessions", []))
    return payload


def load_index_summary() -> dict:
    """Return lightweight index metadata without loading full session details.

    Derives counts from the cached full index (already in memory after any
    previous load_index() call) so there is no extra I/O cost in the common
    case.  Falls back to reading index.json stats block directly when the
    cache is cold — the stats block is at the top of the file but json.load
    still parses the whole file, so this is only a minor win for cold starts;
    the real benefit is not shipping all session records to the caller.
    """
    # When v2 is the source, derive the summary from the (deleted-filtered,
    # already-cached) full index — no extra I/O, and counts stay consistent.
    v2_payload = _load_index_from_v2()
    if v2_payload is not None:
        sessions = v2_payload.get("sessions", [])
        stats = v2_payload.get("stats", {})
        v2_db = INDEX_PATH.parent / "index_v2.sqlite"
        return {
            "total_sessions": int(stats.get("total_sessions") or len(sessions)),
            "by_tool": dict(stats.get("by_tool") or {}),
            "last_updated": v2_payload.get("generated_at"),
            "index_size_bytes": v2_db.stat().st_size if v2_db.exists() else 0,
        }

    if not INDEX_PATH.exists():
        return {
            "total_sessions": 0,
            "by_tool": {},
            "last_updated": None,
            "index_size_bytes": 0,
        }

    stat = INDEX_PATH.stat()
    # Re-use the LRU-cached full parse — no extra disk I/O when warm.
    payload = _load_index_cached(str(INDEX_PATH), stat.st_mtime_ns, stat.st_size)

    # Apply deleted-session filter so counts are consistent with load_index().
    deleted = load_deleted_session_ids()
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


@threadsafe_lru_cache(maxsize=1)
def _load_index_cached(index_path: str, _mtime_ns: int, _size: int):
    with open(index_path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _annotate_display_titles(sessions):
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


# --- Export Path Resolution ---


def resolve_export_path(path_value: Optional[str]) -> Optional[Path]:
    if not path_value:
        return None

    def _safe(candidate: Path) -> Optional[Path]:
        try:
            resolved = candidate.resolve()
            if resolved.is_relative_to(OUTPUT_DIR.resolve()) and resolved.exists():
                return resolved
        except (ValueError, OSError):
            pass
        return None

    raw_path = Path(path_value)
    result = _safe(raw_path)
    if result:
        return result

    marker = "/.ai-history/"
    raw_text = str(path_value)
    idx = raw_text.find(marker)
    if idx != -1:
        relative_tail = raw_text[idx + len(marker) :]
        return _safe(OUTPUT_DIR / relative_tail)

    return None


@threadsafe_lru_cache(maxsize=1)
def load_export_lookup():
    mapping: dict[str, Path] = {}
    projects_dir = OUTPUT_DIR / "projects"
    if not projects_dir.exists():
        return mapping

    for md_file in projects_dir.rglob("*.md"):
        try:
            header = md_file.read_text(encoding="utf-8", errors="replace")[:500]
        except OSError:
            continue
        match = re.search(r"session_id:\s*(\S+)", header)
        if match:
            mapping[match.group(1)] = md_file
    return mapping


# --- Session Building ---


def _tool_from_value(value: Optional[str]) -> Tool:
    try:
        return Tool(value or "")
    except ValueError:
        return Tool.OPENCODE


def build_session_from_export_markdown(
    session_id: str, session_meta: dict, export_path: Path
) -> Optional[UnifiedSession]:
    try:
        text = export_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    title_match = re.search(r"^#\s+(.+)$", text, flags=re.MULTILINE)
    title = title_match.group(1).strip() if title_match else session_meta.get("title")
    if title and (title.lower().startswith("session ") or title.lower().startswith("chat ")):
        title = None

    created_raw = session_meta.get("created")
    updated_raw = session_meta.get("updated")
    try:
        created_at = (
            datetime.fromisoformat(created_raw) if created_raw else datetime.fromtimestamp(0)
        )
    except ValueError:
        created_at = datetime.fromtimestamp(0)
    try:
        updated_at = datetime.fromisoformat(updated_raw) if updated_raw else created_at
    except ValueError:
        updated_at = created_at

    conversation_anchor = text.find("## Conversation")
    if conversation_anchor == -1:
        return None
    convo = text[conversation_anchor:]

    pattern = re.compile(
        r"^###\s+(User|Assistant|System|Tool|Info)\s+\((\d{2}:\d{2}:\d{2})\)\s*$",
        flags=re.MULTILINE,
    )
    matches = list(pattern.finditer(convo))
    if not matches:
        return None

    messages: list[UnifiedMessage] = []
    role_map = {
        "User": Role.USER,
        "Assistant": Role.ASSISTANT,
        "System": Role.SYSTEM,
        "Tool": Role.TOOL,
        "Info": Role.INFO,
    }

    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(convo)
        block = convo[start:end]
        lines = []
        for raw in block.splitlines():
            if raw.strip() == "---":
                continue
            if raw.startswith("> "):
                lines.append(raw[2:])
            else:
                lines.append(raw)
        content = "\n".join(lines).strip()
        if not content:
            continue

        time_part = match.group(2)
        try:
            msg_time = datetime.fromisoformat(f"{created_at.date().isoformat()}T{time_part}")
        except ValueError:
            msg_time = created_at

        messages.append(
            UnifiedMessage(
                role=role_map.get(match.group(1), Role.INFO),
                content=content,
                timestamp=msg_time,
            )
        )

    if not messages:
        return None

    return UnifiedSession(
        tool=_tool_from_value(session_meta.get("tool")),
        session_id=session_id,
        created_at=created_at,
        last_updated=updated_at,
        messages=messages,
        project_path=session_meta.get("project"),
        thread_id=session_meta.get("thread_id"),
        title=title,
        source_path=str(export_path),
    )


__all__ = [
    "OUTPUT_DIR",
    "INDEX_PATH",
    "DELETED_SESSIONS_PATH",
    "threadsafe_lru_cache",
    "load_deleted_session_ids",
    "remember_deleted_session_id",
    "_sanitize_next_url",
    "_apply_deleted_filter",
    "clear_index_cache",
    "clear_sessions_cache",
    "_build_index_from_extractors",
    "load_sessions_for_tool",
    "load_index",
    "load_index_summary",
    "search_index",
    "_annotate_display_titles",
    "resolve_export_path",
    "load_export_lookup",
    "_tool_from_value",
    "build_session_from_export_markdown",
]
