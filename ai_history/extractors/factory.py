from typing import List
from .base import BaseExtractor
from .claude import ClaudeCodeExtractor
from .gemini import GeminiCLIExtractor
from .codex import CodexExtractor
from .warp import WarpExtractor
from .cursor import CursorExtractor
from .vscode import VSCodeCopilotExtractor
from .copilot import CopilotCLIExtractor
from .opencode import OpenCodeExtractor
from .antigravity import AntigravityExtractor


def get_all_extractors() -> List[BaseExtractor]:
    return [
        ClaudeCodeExtractor(),
        GeminiCLIExtractor(),
        CodexExtractor(),
        WarpExtractor(),
        CursorExtractor(),
        VSCodeCopilotExtractor(),
        CopilotCLIExtractor(),
        OpenCodeExtractor(),
        AntigravityExtractor(),
    ]
