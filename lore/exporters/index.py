import json
import os
import re
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from ..core.models import UnifiedSession


def _stat_mtime_ns(path_value: Optional[str]) -> Optional[int]:
    """Return the mtime_ns of ``path_value`` if it exists, else None."""
    if not path_value:
        return None
    try:
        return os.stat(path_value).st_mtime_ns
    except OSError:
        return None


def is_low_quality_title(text: str) -> bool:
    """True if ``text`` is noise that should not be used as a session title.

    Catches command/caveat boilerplate, sandbox/approval chatter, and too-short or
    non-alphabetic strings. Used both when building the index and when rendering a
    live session, so the two paths agree (#68).
    """
    lowered = (text or "").lower().strip()
    if not lowered:
        return True

    # Drop any leading XML-ish tag wrapper (e.g. "<local-command-caveat>") so the
    # boilerplate it wraps is still recognised below (#68).
    lowered = re.sub(r"^<[^>]*>", "", lowered).strip()
    if not lowered:
        return True

    normalized = re.sub(r"^[^a-z0-9]+", "", lowered)

    low_quality_prefixes = (
        "local-command-",
        "caveat: the messages below were generated",
        "user exited claude code session",
        "conversation started",
        "session ",
        "agents.md instructions",
        "instructions for /home",
        "command-name",
        "command-message",
        "command-args",
        "login successful",
        "invalid api key",
        "api error",
        "generate a file named agents.md",
    )
    if any(normalized.startswith(prefix) for prefix in low_quality_prefixes):
        return True

    low_quality_fragments = (
        "on-request workspace-write",
        "workspace-write restricted",
        "sandbox",
        "approval",
    )
    if any(fragment in normalized for fragment in low_quality_fragments):
        return True

    if len(lowered) < 8:
        return True

    alpha_chars = sum(1 for ch in lowered if ch.isalpha())
    if alpha_chars < max(3, len(lowered) // 6):
        return True

    return False


class IndexBuilder:
    """Build search index for sessions."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.index_path = output_dir / "index.json"
        self.sqlite_path = output_dir / "index.sqlite"

    def build_index(
        self,
        sessions: List[UnifiedSession],
        export_paths: Dict[str, Path],
        reused_entries: Optional[List[Dict]] = None,
        reused_sessions: Optional[List[UnifiedSession]] = None,
    ) -> None:
        """Build and save the search index.

        When ``reused_entries`` is provided, those pre-built session dicts are
        included verbatim in the JSON index (no re-extraction of
        keywords/search_text). They must be disjoint from ``sessions`` by id.

        ``reused_sessions`` are the *full* UnifiedSession objects behind those
        same reused entries. Incremental sync has already extracted them, so
        the v2 store receives them as complete sessions (with message rows)
        rather than metadata-only — this keeps the v2 ``messages`` table
        complete after an incremental sync (#35).
        """
        ignored_ids = self._load_ignored()
        if ignored_ids:
            sessions = [s for s in sessions if s.session_id not in ignored_ids]
            if reused_entries:
                reused_entries = [
                    entry for entry in reused_entries if entry.get("id") not in ignored_ids
                ]

        index = {
            "version": "1.0.0",
            "generated_at": datetime.now().isoformat(),
            "stats": {},
            "sessions": [],
            "search_index": {},
        }

        keyword_index: Dict[str, List[str]] = {}
        # Titles computed below are reused for the v2 dual-write so v2 and the
        # JSON index agree on every session title.
        inferred_titles: Dict[str, str] = {}
        # prompt_outline / export_path per session, denormalised onto the v2
        # sessions row so the v2 reader needs no joins.
        v2_extras: Dict[str, Dict] = {}

        if reused_entries:
            for entry in reused_entries:
                index["sessions"].append(entry)
                for kw in entry.get("keywords") or []:
                    keyword_index.setdefault(kw, []).append(entry.get("id", ""))

        for session in sessions:
            export_path = export_paths.get(session.session_id, "")
            prompt_count = self._count_prompts(session)
            prompt_outline = self._extract_prompt_outline(session)
            inferred_title = self._infer_title(session, prompt_outline)
            inferred_titles[session.session_id] = inferred_title
            v2_extras[session.session_id] = {
                "prompt_outline": prompt_outline,
                "export_path": str(export_path) if export_path else None,
            }

            # Extract keywords from content
            keywords = self._extract_keywords(session)

            session_entry = {
                "id": session.session_id,
                "tool": session.tool.value,
                "project": session.project_path,
                "thread_id": session.thread_id,
                "title": inferred_title,
                "created": session.created_at.isoformat(),
                "updated": session.last_updated.isoformat(),
                "messages": session.message_count,
                "prompts": prompt_count,
                "tokens": session.total_tokens,
                "prompt_outline": prompt_outline,
                "export_path": str(export_path) if export_path else None,
                "git_branch": getattr(session, "git_branch", None),
                "git_commit": getattr(session, "git_commit", None),
                "source_path": session.source_path,
                "source_mtime": _stat_mtime_ns(session.source_path),
                "keywords": keywords,
                "search_text": self._build_search_text(session),
            }
            index["sessions"].append(session_entry)

            # Build keyword index
            for kw in keywords:
                if kw not in keyword_index:
                    keyword_index[kw] = []
                keyword_index[kw].append(session.session_id)

        index["stats"] = self._compute_stats_from_entries(index["sessions"])
        index["search_index"] = keyword_index

        # Atomic write: write to temp file then os.replace to avoid partial reads on SIGINT
        from ..utils.paths import restrict_file, secure_dir

        secure_dir(self.output_dir)  # 0700 — holds session transcripts (#41)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=self.output_dir,
            delete=False,
            suffix=".tmp",
        ) as tmp:
            json.dump(index, tmp, indent=2)
            tmp_path = tmp.name
        os.replace(tmp_path, self.index_path)
        restrict_file(self.index_path)  # 0600 — index.json holds session content

        self._build_sqlite_index(sessions, export_paths, reused_entries=reused_entries)

        # Dual-write into the v2 SQLite store (issue #44). Best-effort: a v2
        # failure is logged and never breaks the legacy index above.
        #
        # When the caller supplies reused_sessions (full UnifiedSession objects
        # from incremental sync), the v2 store gets every session as a complete
        # row with message rows — keeping its messages table complete (#35).
        # Otherwise it falls back to the metadata-only reused_entries dicts.
        from ..storage.writer import write_sessions_safe

        if reused_sessions:
            all_v2_sessions = list(sessions) + list(reused_sessions)
            write_sessions_safe(
                self.output_dir,
                all_v2_sessions,
                titles=inferred_titles,
                extras=v2_extras,
            )
        else:
            write_sessions_safe(
                self.output_dir,
                sessions,
                titles=inferred_titles,
                reused_entries=reused_entries,
                extras=v2_extras,
            )

    def _compute_stats_from_entries(self, entries: List[Dict]) -> Dict:
        """Compute statistics from already-built session dict entries."""
        by_tool: Dict[str, int] = {}
        by_project: Dict[str, int] = {}
        total_messages = 0
        for entry in entries:
            tool_name = str(entry.get("tool") or "")
            if tool_name:
                by_tool[tool_name] = by_tool.get(tool_name, 0) + 1
            project = entry.get("project")
            if project:
                by_project[project] = by_project.get(project, 0) + 1
            total_messages += int(entry.get("messages") or 0)
        return {
            "total_sessions": len(entries),
            "total_messages": total_messages,
            "by_tool": by_tool,
            "by_project": by_project,
        }

    def _compute_stats(self, sessions: List[UnifiedSession]) -> Dict:
        """Compute statistics from sessions."""
        by_tool: Dict[str, int] = {}
        by_project: Dict[str, int] = {}

        for session in sessions:
            tool_name = session.tool.value
            by_tool[tool_name] = by_tool.get(tool_name, 0) + 1

            if session.project_path:
                by_project[session.project_path] = by_project.get(session.project_path, 0) + 1

        return {
            "total_sessions": len(sessions),
            "total_messages": sum(s.message_count for s in sessions),
            "by_tool": by_tool,
            "by_project": by_project,
        }

    def _count_prompts(self, session: UnifiedSession) -> int:
        return session.user_prompt_count

    def _extract_prompt_outline(self, session: UnifiedSession) -> str:
        skip_markers = (
            "caveat: the messages below were generated by the user",
            "do not respond to these messages",
            "messages below were generated by the user while running local commands",
            "<command-name>",
            "<command-message>",
            "<command-args>",
            "# agents.md instructions",
            "agents.md instructions",
            "## instructions",
        )
        for msg in session.messages:
            role = getattr(msg, "role", None)
            if getattr(role, "value", role) != "user":
                continue
            text = (msg.content or "").strip()
            if not text:
                continue
            lowered = text.lower()
            if any(marker in lowered for marker in skip_markers):
                continue
            text = self._clean_title_text(text)
            if not text:
                continue
            if self._is_low_quality_title(text):
                continue
            return text[:140]
        return ""

    def _infer_title(self, session: UnifiedSession, prompt_outline: str) -> str:
        suffix = session.session_id[-8:] if session.session_id else "session"

        if session.title and session.title.strip():
            native = self._clean_title_text(session.title)
            if native and not self._is_low_quality_title(native):
                return native[:80]

        if prompt_outline:
            cleaned = self._clean_title_text(prompt_outline)
            if self._is_low_quality_title(cleaned):
                cleaned = ""
            if cleaned:
                base = cleaned[:64]
                if base.endswith(f"· {suffix}"):
                    return base
                return f"{base} · {suffix}"

        date_label = session.created_at.strftime("%Y-%m-%d")
        tool_label = session.tool.value.replace("-", " ").title()
        return f"{tool_label} {date_label} • {suffix}"

    def _clean_title_text(self, text: str) -> str:
        cleaned = re.sub(r"^\[Tool Result\]\s*", "", text or "").strip()
        cleaned = re.sub(r"```.*?```", " ", cleaned, flags=re.DOTALL)
        cleaned = re.sub(r"<[^>]+>", " ", cleaned)
        cleaned = cleaned.replace("`", " ")
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def _is_low_quality_title(self, text: str) -> bool:
        return is_low_quality_title(text)

    def _extract_keywords(self, session: UnifiedSession) -> List[str]:
        """Extract searchable keywords from session."""
        keywords = set()

        # From title
        if session.title:
            words = re.findall(r"\b\w{3,}\b", session.title.lower())
            keywords.update(words)

        # From messages (limited to avoid huge indexes)
        for msg in session.messages[:20]:  # First 20 messages
            if not msg.content:
                continue
            words = re.findall(r"\b\w{4,}\b", msg.content.lower())
            keywords.update(words[:50])  # First 50 words per message

        # Filter out common words
        stopwords = {
            "this",
            "that",
            "with",
            "have",
            "will",
            "from",
            "they",
            "been",
            "were",
            "said",
            "each",
            "which",
            "their",
            "there",
            "would",
            "about",
        }
        keywords -= stopwords

        return list(keywords)[:100]  # Limit to 100 keywords

    def _build_search_text(self, session: UnifiedSession) -> str:
        parts: List[str] = []

        if session.title:
            parts.append(session.title)

        for msg in session.messages[:30]:
            if msg.content:
                parts.append(msg.content)

        text = " ".join(parts).lower()
        return text[:20000]

    def _build_sqlite_index(
        self,
        sessions: List[UnifiedSession],
        export_paths: Dict[str, Path],
        reused_entries: Optional[List[Dict]] = None,
    ) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self.sqlite_path)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    tool TEXT,
                    project TEXT,
                    thread_id TEXT,
                    title TEXT,
                    created TEXT,
                    updated TEXT,
                    messages INTEGER,
                    prompts INTEGER,
                    prompt_outline TEXT,
                    export_path TEXT,
                    search_text TEXT
                )
            """
            )
            columns = {row[1] for row in conn.execute("PRAGMA table_info(sessions)").fetchall()}
            if "prompts" not in columns:
                conn.execute("ALTER TABLE sessions ADD COLUMN prompts INTEGER")
            if "prompt_outline" not in columns:
                conn.execute("ALTER TABLE sessions ADD COLUMN prompt_outline TEXT")
            conn.execute("DELETE FROM sessions")

            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_tool ON sessions(tool)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_project ON sessions(project)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_created ON sessions(created)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_thread_id ON sessions(thread_id)")

            conn.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS sessions_fts
                USING fts5(id, title, project, tool, search_text)
            """
            )
            conn.execute("DELETE FROM sessions_fts")

            rows = []
            fts_rows = []
            if reused_entries:
                for entry in reused_entries:
                    rows.append(
                        (
                            entry.get("id"),
                            entry.get("tool"),
                            entry.get("project"),
                            entry.get("thread_id"),
                            entry.get("title"),
                            entry.get("created"),
                            entry.get("updated"),
                            int(entry.get("messages") or 0),
                            int(entry.get("prompts") or 0),
                            entry.get("prompt_outline"),
                            entry.get("export_path"),
                            entry.get("search_text") or "",
                        )
                    )
                    fts_rows.append(
                        (
                            entry.get("id"),
                            entry.get("title") or "",
                            entry.get("project") or "",
                            entry.get("tool") or "",
                            entry.get("search_text") or "",
                        )
                    )
            for session in sessions:
                export_path = export_paths.get(session.session_id, "")
                search_text = self._build_search_text(session)
                prompt_count = self._count_prompts(session)
                prompt_outline = self._extract_prompt_outline(session)
                inferred_title = self._infer_title(session, prompt_outline)
                rows.append(
                    (
                        session.session_id,
                        session.tool.value,
                        session.project_path,
                        session.thread_id,
                        inferred_title,
                        session.created_at.isoformat(),
                        session.last_updated.isoformat(),
                        session.message_count,
                        prompt_count,
                        prompt_outline,
                        str(export_path) if export_path else None,
                        search_text,
                    )
                )
                fts_rows.append(
                    (
                        session.session_id,
                        inferred_title or "",
                        session.project_path or "",
                        session.tool.value,
                        search_text,
                    )
                )

            conn.executemany(
                """
                INSERT OR REPLACE INTO sessions (
                    id, tool, project, thread_id, title, created, updated,
                    messages, prompts, prompt_outline, export_path, search_text
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                rows,
            )
            conn.executemany(
                """
                INSERT INTO sessions_fts (id, title, project, tool, search_text)
                VALUES (?, ?, ?, ?, ?)
            """,
                fts_rows,
            )
            conn.commit()
        finally:
            conn.close()

    def _load_ignored(self) -> set:
        ignore_path = self.output_dir / "ignored.json"
        if not ignore_path.exists():
            return set()
        try:
            data = json.loads(ignore_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                values = data.get("session_ids", [])
            else:
                values = data
            return set(values or [])
        except Exception:
            return set()
