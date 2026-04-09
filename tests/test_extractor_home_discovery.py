from ai_history.extractors.antigravity import AntigravityExtractor
from ai_history.extractors.claude import ClaudeCodeExtractor
from ai_history.extractors.codex import CodexExtractor
from ai_history.extractors.copilot import CopilotCLIExtractor
from ai_history.extractors.cursor import CursorExtractor
from ai_history.extractors.gemini import GeminiCLIExtractor
from ai_history.extractors.vscode import VSCodeCopilotExtractor
from ai_history.extractors.warp import WarpExtractor


def test_directory_extractors_discover_nested_home_locations(monkeypatch, tmp_path):
    home = tmp_path / "home"
    nested = home / "projects" / "migrated"

    paths = {
        "claude": nested / ".claude" / "projects",
        "gemini": nested / ".gemini" / "tmp",
        "codex": nested / ".codex" / "sessions",
        "copilot": nested / ".copilot" / "session-state",
        "vscode": nested / ".config" / "Code" / "User" / "workspaceStorage",
        "antigravity": nested / ".gemini" / "antigravity",
    }

    (paths["claude"]).mkdir(parents=True, exist_ok=True)
    (paths["gemini"]).mkdir(parents=True, exist_ok=True)
    (paths["codex"]).mkdir(parents=True, exist_ok=True)
    (paths["copilot"]).mkdir(parents=True, exist_ok=True)
    (paths["vscode"]).mkdir(parents=True, exist_ok=True)
    (paths["antigravity"] / "brain").mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("AI_HISTORY_HOME_SCAN_DEPTH", "6")
    monkeypatch.setenv("AI_HISTORY_HOME_SCAN_LIMIT", "32")

    claude = ClaudeCodeExtractor()
    gemini = GeminiCLIExtractor()
    codex = CodexExtractor()
    copilot = CopilotCLIExtractor()
    vscode = VSCodeCopilotExtractor()
    antigravity = AntigravityExtractor()

    assert paths["claude"].resolve() in {path.resolve() for path in claude.base_paths}
    assert paths["gemini"].resolve() in {path.resolve() for path in gemini.base_paths}
    assert paths["codex"].resolve() in {path.resolve() for path in codex.session_roots}
    assert paths["copilot"].resolve() in {
        path.resolve() for path in copilot.session_state_dirs
    }
    assert paths["vscode"].resolve() in {
        path.resolve() for path in vscode.workspace_roots
    }
    assert paths["antigravity"].resolve() in {
        path.resolve() for path in antigravity.base_paths
    }


def test_db_extractors_discover_nested_home_locations(monkeypatch, tmp_path):
    home = tmp_path / "home"
    nested = home / "archives" / "backup"

    cursor_db = nested / ".config" / "Cursor" / "User" / "globalStorage" / "state.vscdb"
    warp_db = nested / ".local" / "state" / "warp-terminal" / "warp.sqlite"
    cursor_db.parent.mkdir(parents=True, exist_ok=True)
    warp_db.parent.mkdir(parents=True, exist_ok=True)
    cursor_db.touch()
    warp_db.touch()

    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("AI_HISTORY_HOME_SCAN_DEPTH", "6")
    monkeypatch.setenv("AI_HISTORY_HOME_SCAN_LIMIT", "32")

    cursor = CursorExtractor()
    warp = WarpExtractor()

    assert cursor_db.resolve() in {path.resolve() for path in cursor.db_paths}
    assert warp_db.resolve() in {path.resolve() for path in warp.db_paths}
