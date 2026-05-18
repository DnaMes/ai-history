"""Shared extractor-iteration and index-building logic.

This module holds the "iterate available extractors and collect
sessions" routine that used to be copy-pasted into ``web_data`` (twice),
``mcp`` and the CLI. It is framework-free: no Flask, no interface
imports.

Both the web interface and the MCP server build on these helpers.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Callable, Iterable, Optional

from ai_history.core.models import UnifiedSession
from ai_history.exporters.index import IndexBuilder, _stat_mtime_ns
from ai_history.extractors.base import BaseExtractor
from ai_history.extractors.factory import get_all_extractors
from ai_history.titles.generator import TitleGenerator, TitleStrategy

logger = logging.getLogger(__name__)


class ActionJobCancelledError(RuntimeError):
    """Raised when a long-running build/extraction is cancelled by the user.

    Defined in the (framework-free) service layer so both ``services`` and
    the Flask-coupled interface modules can reference the same exception
    type. ``ai_history.interfaces.web_utils`` re-exports it for backwards
    compatibility.
    """


def select_extractors(
    tool_filter: Optional[str] = None,
    extractors: Optional[Iterable[BaseExtractor]] = None,
) -> list[BaseExtractor]:
    """Return the available extractors, optionally filtered to one tool."""
    candidates = list(extractors) if extractors is not None else get_all_extractors()
    return [
        extractor
        for extractor in candidates
        if extractor.is_available() and (not tool_filter or extractor.tool.value == tool_filter)
    ]


def collect_sessions(
    tool_filter: Optional[str] = None,
    *,
    apply_titles: bool = True,
    deleted_ids: Optional[set[str]] = None,
) -> list[UnifiedSession]:
    """Iterate available extractors and collect their sessions.

    This is the shared core of the old ``load_sessions_for_tool`` and the
    MCP server's ``build_index_if_missing`` loop.

    Args:
        tool_filter: When set, only the matching tool's extractor runs.
        apply_titles: When True, a fast ``TitleGenerator`` annotates each
            session's title in place.
        deleted_ids: Session ids to drop from the result (tombstones).

    Extractor failures are logged and skipped — one broken tool never
    aborts the whole collection.
    """
    title_generator = TitleGenerator(strategy=TitleStrategy.FAST) if apply_titles else None
    sessions: list[UnifiedSession] = []

    for extractor in select_extractors(tool_filter):
        try:
            extracted = list(extractor.extract_sessions())
        except Exception as exc:
            logger.debug(
                "Extractor %s failed during session collection: %s",
                extractor.tool.value,
                exc,
            )
            continue
        if title_generator is not None:
            for session in extracted:
                title = title_generator.generate(session, force=False)
                if title:
                    session.title = title
        sessions.extend(extracted)

    if deleted_ids:
        sessions = [s for s in sessions if s.session_id not in deleted_ids]
    return sessions


def build_index_if_missing(
    output_dir: Path,
    index_path: Path,
) -> None:
    """Build a minimal index from extractors if ``index_path`` is absent.

    Used by the MCP server, which does not need the web app's incremental
    rebuild logic — a one-shot full extraction is sufficient.
    """
    if index_path.exists():
        return
    sessions: list[UnifiedSession] = []
    for extractor in get_all_extractors():
        if not extractor.is_available():
            continue
        try:
            sessions.extend(list(extractor.extract_sessions()))
        except Exception as exc:
            logger.debug(
                "Extractor %s failed during build_index_if_missing: %s",
                extractor.tool.value,
                exc,
            )
            continue
    IndexBuilder(output_dir).build_index(sessions, {})


def build_search_index(
    output_dir: Path,
    index_path: Path,
    *,
    deleted_ids: Optional[set[str]] = None,
    tool_filter: Optional[str] = None,
    progress_callback: Optional[Callable[[int, str], None]] = None,
    should_stop: Optional[Callable[[], bool]] = None,
    incremental: bool = True,
) -> list[dict]:
    """Build the full search index from extractors.

    When ``incremental=True`` (default) sessions already present in the
    existing index whose source-file mtime hasn't changed are reused
    verbatim instead of being re-processed by :class:`IndexBuilder`. Set
    ``incremental=False`` to force a full rebuild.

    Returns a list of ``{"extractor": ..., "error": ...}`` dicts, one per
    extractor that failed.
    """
    selected = select_extractors(tool_filter)

    existing_by_id: dict[str, dict] = {}
    if incremental and index_path.exists():
        try:
            with open(index_path, "r", encoding="utf-8") as handle:
                existing_payload = json.load(handle)
            for entry in existing_payload.get("sessions", []) or []:
                sid = str(entry.get("id") or "")
                if sid:
                    existing_by_id[sid] = entry
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Failed to read existing index for incremental build: %s", exc)

    sessions: list[UnifiedSession] = []
    reused_entries: list[dict] = []
    # The full UnifiedSession objects behind reused_entries — incremental sync
    # has already extracted them (messages included), so we hand them to the
    # v2 store as complete sessions instead of metadata-only rows (#35).
    reused_sessions: list[UnifiedSession] = []
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
            extracted_sessions: list[UnifiedSession] = []
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

    deleted = deleted_ids or set()
    filtered = [session for session in sessions if session.session_id not in deleted]
    reused_filtered = [entry for entry in reused_entries if entry.get("id") not in deleted]
    reused_sessions_filtered = [s for s in reused_sessions if s.session_id not in deleted]
    IndexBuilder(output_dir).build_index(
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
