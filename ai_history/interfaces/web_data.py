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
from typing import Optional

from ai_history.core.models import Role, Tool, UnifiedMessage, UnifiedSession
from ai_history.exporters.index import IndexBuilder
from ai_history.extractors.factory import get_all_extractors
from ai_history.titles.generator import TitleGenerator, TitleStrategy

from .web_utils import ActionJobCancelledError

logger = logging.getLogger(__name__)

# Thread-safe LRU cache wrapper
_threadsafe_cache_locks: dict = {}
_threadsafe_cache_lock = threading.Lock()


def threadsafe_lru_cache(maxsize=128):
    """Thread-safe LRU cache decorator for use in multi-threaded Flask applications."""
    import threading

    def decorator(func):
        cached_func = lru_cache(maxsize=maxsize)(func)
        cache_lock = threading.Lock()

        def wrapper(*args, **kwargs):
            with cache_lock:
                return cached_func(*args, **kwargs)

        # Copy cache control methods from the cached function
        wrapper.cache_clear = cached_func.cache_clear  # type: ignore
        wrapper.cache_info = cached_func.cache_info  # type: ignore
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
    _load_deleted_session_ids_cached.cache_clear()
    load_export_lookup.cache_clear()


def clear_sessions_cache():
    load_sessions_for_tool.cache_clear()


# --- Index Building ---


def _build_index_from_extractors(
    tool_filter: Optional[str] = None,
    progress_callback=None,
    should_stop=None,
):
    extractors = get_all_extractors()
    selected = [
        extractor
        for extractor in extractors
        if extractor.is_available() and (not tool_filter or extractor.tool.value == tool_filter)
    ]

    sessions = []
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
                title = title_generator.generate(session, force=False)
                if title:
                    session.title = title
                extracted_sessions.append(session)
            sessions.extend(extracted_sessions)
        except ActionJobCancelledError:
            raise
        except Exception as exc:
            logger.debug("Extractor %s failed during index build: %s", extractor.tool.value, exc)
            continue

    deleted = load_deleted_session_ids()
    filtered = [session for session in sessions if session.session_id not in deleted]
    IndexBuilder(OUTPUT_DIR).build_index(filtered, {})

    if progress_callback:
        progress_callback(62, "Index written")


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


def load_index():
    if not INDEX_PATH.exists():
        try:
            _build_index_from_extractors()
        except Exception as exc:
            logger.warning("Failed to build index from extractors: %s", exc)
            return {"stats": {}, "sessions": []}
    if not INDEX_PATH.exists():
        return {"stats": {}, "sessions": []}
    stat = INDEX_PATH.stat()
    payload = _load_index_cached(str(INDEX_PATH), stat.st_mtime_ns, stat.st_size)
    payload = _apply_deleted_filter(payload)
    payload["sessions"] = _annotate_display_titles(payload.get("sessions", []))
    return payload


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
    "_annotate_display_titles",
    "resolve_export_path",
    "load_export_lookup",
    "_tool_from_value",
    "build_session_from_export_markdown",
]
