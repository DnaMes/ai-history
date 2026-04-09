from abc import ABC, abstractmethod
import logging
import os
from typing import Iterator
from ..core.models import Role, TitleSource, Tool, UnifiedSession


logger = logging.getLogger(__name__)


class BaseExtractor(ABC):
    """Base class for all tool-specific extractors."""

    # Minimum thresholds for importing sessions
    MIN_MESSAGES = 1
    MIN_CONTENT_SIZE = 0
    MIN_USER_PROMPTS = 1

    @property
    @abstractmethod
    def tool(self) -> Tool:
        pass

    @abstractmethod
    def extract_sessions(self) -> Iterator[UnifiedSession]:
        pass

    def is_available(self) -> bool:
        """Check if the tool's data is available on this system."""
        return True

    def _normalize_session(self, session: UnifiedSession) -> None:
        if not session.thread_id:
            try:
                from ..utils.paths import make_thread_id

                session.thread_id = make_thread_id(project_path=session.project_path)
            except Exception as exc:
                logger.debug(
                    "Failed to generate thread id for session %s: %s",
                    session.session_id,
                    exc,
                )

        if not session.thread_id:
            session.thread_id = f"session:{session.session_id[:12]}"

        if session.title and session.title.strip():
            if session.title_source is None:
                session.title_source = TitleSource.NATIVE
            return

        first_user_message = ""
        for message in session.messages:
            if message.role == Role.USER and (message.content or "").strip():
                first_user_message = message.content.strip()
                break

        if first_user_message:
            words = first_user_message.split()[:10]
            title = " ".join(words)
            if len(title) > 80:
                title = title[:77] + "..."
            session.title = title
            session.title_source = TitleSource.FIRST_MESSAGE
            return

        session.title = f"{session.tool.value.replace('-', ' ').title()} Session {session.created_at.strftime('%Y-%m-%d')}"
        session.title_source = TitleSource.FALLBACK


    def _effective_thresholds(self) -> tuple[int, int, int]:
        profile = os.environ.get("AI_HISTORY_IMPORT_PROFILE", "relaxed").strip().lower()
        if profile == "strict":
            return (3, 2048, 2)
        return (self.MIN_MESSAGES, self.MIN_CONTENT_SIZE, self.MIN_USER_PROMPTS)

    def should_import_session(self, session: UnifiedSession) -> bool:
        """
        Determine if a session should be imported based on quality thresholds.

        A session is imported if:
        - It has >= MIN_MESSAGES messages, OR
        - Total content size >= MIN_CONTENT_SIZE bytes

        This filters out test sessions, typos, and abandoned conversations
        while preserving sessions with substantial content.
        """
        self._normalize_session(session)

        min_messages, min_content_size, min_user_prompts = self._effective_thresholds()

        message_count = len(session.messages)
        user_prompt_count = session.user_prompt_count

        if user_prompt_count < min_user_prompts:
            return False

        # Always import if enough messages
        if message_count >= min_messages:
            return True

        # For short sessions, check content size
        total_content_size = sum(len(msg.content or "") for msg in session.messages)

        return total_content_size >= min_content_size
