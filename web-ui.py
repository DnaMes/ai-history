#!/usr/bin/env python3
"""
ai-history Web UI v2.0

A modern Flask-based web dashboard for browsing and searching AI chat history.
Inspired by SpecStory's clean, developer-focused design.

Features:
- Modern, polished UI with smooth animations
- Proper Markdown rendering with syntax highlighting
- Keyboard shortcuts (Cmd+K for search, Escape to close)
- Sticky navigation with quick dashboard access
- Session filtering by tool, project, date
- Full-text search
- Export to Markdown
- Google Drive sync preparation

Usage:
    python3 web-ui.py

Then open http://localhost:5000 in your browser.

Requirements:
    pip install flask markdown
"""

import json
import re
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
from functools import lru_cache, wraps

try:
    from flask import (
        Flask,
        render_template_string,
        request,
        jsonify,
        Response,
        redirect,
        url_for,
    )
except ImportError:
    print("Flask not installed. Run: pip install flask")
    sys.exit(1)

try:
    from markupsafe import escape

    HAS_MARKUPSAFE = True
except ImportError:
    HAS_MARKUPSAFE = False
    print(
        "Warning: markupsafe not found. Input sanitization disabled. Run: pip install markupsafe"
    )

try:
    import markdown

    HAS_MARKDOWN = True
except ImportError:
    HAS_MARKDOWN = False

sys.path.insert(0, str(Path(__file__).parent))
import importlib.util

spec = importlib.util.spec_from_file_location(
    "ai_history", Path(__file__).parent / "ai-history.py"
)
ai_history = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ai_history)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

WEB_USERNAME = os.getenv("WEB_USERNAME", "admin")
WEB_PASSWORD = os.getenv("WEB_PASSWORD")

if not WEB_PASSWORD:
    import secrets

    WEB_PASSWORD = secrets.token_urlsafe(16)
    print(
        f"\n⚠️  WARNING: No WEB_PASSWORD set. Using auto-generated password: {WEB_PASSWORD}"
    )
    print(f"Set WEB_PASSWORD environment variable for persistence.\n")

# Configuration
OUTPUT_DIR = Path.home() / ".ai-history"
INDEX_PATH = OUTPUT_DIR / "index.json"


def check_auth(username: str, password: str) -> bool:
    """Validate credentials."""
    return username == WEB_USERNAME and password == WEB_PASSWORD


def authenticate():
    """Send 401 with auth required."""
    return Response(
        "Authentication required. Set WEB_USERNAME and WEB_PASSWORD environment variables.",
        401,
        {"WWW-Authenticate": 'Basic realm="ai-history"'},
    )


def requires_auth(f):
    """Decorator to require HTTP Basic Auth on routes."""

    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)

    return decorated


def sanitize_input(
    value: str, max_length: int = 200, allow_path_chars: bool = False
) -> str:
    """Sanitize user input to prevent XSS and injection."""
    if not value:
        return ""

    if not HAS_MARKUPSAFE:
        return str(value)[:max_length]

    sanitized = escape(str(value))

    if not allow_path_chars:
        dangerous_patterns = [
            "<",
            ">",
            "&",
            '"',
            "'",
            "`",
            "${",
            "$(",
            ";",
            "|",
            "\n",
            "\r",
        ]
        for pattern in dangerous_patterns:
            sanitized = sanitized.replace(pattern, "")

    return str(sanitized)[:max_length]


def validate_session_id(session_id: str) -> bool:
    """Validate session ID format to prevent injection."""
    if not session_id or len(session_id) > 256:
        return False

    import string

    allowed = string.ascii_letters + string.digits + "-_"
    return all(c in allowed for c in session_id)


# Tool colors and icons
TOOL_STYLES = {
    "claude-code": {"color": "#b794f4", "bg": "#553c9a40", "icon": "🤖"},
    "cursor": {"color": "#a0aec0", "bg": "#2d3748", "icon": "⌨️"},
    "gemini-cli": {"color": "#63b3ed", "bg": "#1a365d40", "icon": "✨"},
    "warp": {"color": "#4fd1c5", "bg": "#234e5240", "icon": "🚀"},
    "codex": {"color": "#68d391", "bg": "#22543d40", "icon": "📦"},
    "vscode-copilot": {"color": "#90cdf4", "bg": "#2c528940", "icon": "🧑‍✈️"},
    "copilot-cli": {"color": "#d6bcfa", "bg": "#44337a40", "icon": "💻"},
}

# Modern HTML Template
BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} - ai-history</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css">
    <style>
        :root, :root[data-theme="dark"] {
            --bg-primary: #0a0a0b;
            --bg-secondary: #111113;
            --bg-tertiary: #18181b;
            --bg-elevated: #1f1f23;
            --bg-hover: #27272a;
            --text-primary: #fafafa;
            --text-secondary: #a1a1aa;
            --text-muted: #71717a;
            --accent: #3b82f6;
            --accent-hover: #60a5fa;
            --accent-subtle: #3b82f620;
            --success: #22c55e;
            --success-subtle: #22c55e20;
            --warning: #f59e0b;
            --error: #ef4444;
            --border: #27272a;
            --border-subtle: #1f1f23;
            --shadow: 0 4px 6px -1px rgba(0,0,0,0.3), 0 2px 4px -2px rgba(0,0,0,0.3);
            --shadow-lg: 0 10px 15px -3px rgba(0,0,0,0.4), 0 4px 6px -4px rgba(0,0,0,0.4);
            --radius: 12px;
            --radius-sm: 8px;
            --radius-lg: 16px;
        }

        :root[data-theme="light"] {
            --bg-primary: #ffffff;
            --bg-secondary: #f5f5f7;
            --bg-tertiary: #e5e5e7;
            --bg-elevated: #ffffff;
            --bg-hover: #d4d4d8;
            --text-primary: #18181b;
            --text-secondary: #52525b;
            --text-muted: #a1a1aa;
            --accent: #3b82f6;
            --accent-hover: #2563eb;
            --accent-subtle: #3b82f615;
            --success: #16a34a;
            --success-subtle: #16a34a20;
            --warning: #ca8a04;
            --error: #dc2626;
            --border: #e5e5e7;
            --border-subtle: #d4d4d8;
            --shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -2px rgba(0,0,0,0.1);
            --shadow-lg: 0 10px 15px -3px rgba(0,0,0,0.15), 0 4px 6px -4px rgba(0,0,0,0.15);
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
            min-height: 100vh;
        }

        /* Smooth scrolling */
        html { scroll-behavior: smooth; }

        /* Scrollbar styling */
        ::-webkit-scrollbar { width: 8px; height: 8px; }
        ::-webkit-scrollbar-track { background: var(--bg-secondary); }
        ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }

        /* Header - Sticky */
        header {
            position: sticky;
            top: 0;
            z-index: 100;
            background: var(--bg-secondary);
            border-bottom: 1px solid var(--border);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
        }

        .header-inner {
            max-width: 1400px;
            margin: 0 auto;
            padding: 12px 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .logo {
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 1.25rem;
            font-weight: 700;
            color: var(--text-primary);
            text-decoration: none;
            transition: opacity 0.2s;
        }

        .logo:hover { opacity: 0.8; }

        .logo-icon {
            width: 32px;
            height: 32px;
            background: linear-gradient(135deg, var(--accent), #8b5cf6);
            border-radius: var(--radius-sm);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
        }

        nav {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        nav a {
            color: var(--text-secondary);
            text-decoration: none;
            padding: 8px 16px;
            border-radius: var(--radius-sm);
            font-size: 0.9rem;
            font-weight: 500;
            transition: all 0.2s;
        }

        nav a:hover {
            color: var(--text-primary);
            background: var(--bg-hover);
        }

        nav a.active {
            color: var(--text-primary);
            background: var(--bg-tertiary);
        }

        .search-trigger {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 14px;
            background: var(--bg-tertiary);
            border: 1px solid var(--border);
            border-radius: var(--radius-sm);
            color: var(--text-muted);
            font-size: 0.85rem;
            cursor: pointer;
            transition: all 0.2s;
        }

        .search-trigger:hover {
            border-color: var(--text-muted);
            color: var(--text-secondary);
        }

        .kbd {
            background: var(--bg-elevated);
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.75rem;
        }

        /* Main Content */
        main {
            max-width: 1400px;
            margin: 0 auto;
            padding: 32px 24px;
        }

        /* Page Header */
        .page-header {
            margin-bottom: 32px;
        }

        .page-header h1 {
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 8px;
        }

        .page-header p {
            color: var(--text-secondary);
            font-size: 1rem;
        }

        /* Stats Grid */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 40px;
        }

        .stat-card {
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 24px;
            transition: all 0.2s;
        }

        .stat-card:hover {
            border-color: var(--accent);
            transform: translateY(-2px);
            box-shadow: var(--shadow);
        }

        .stat-label {
            font-size: 0.85rem;
            color: var(--text-muted);
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 8px;
        }

        .stat-value {
            font-size: 2.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, var(--accent), #8b5cf6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        /* Tools Grid */
        .tools-section {
            margin-bottom: 40px;
        }

        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }

        .section-title {
            font-size: 1.25rem;
            font-weight: 600;
        }

        .tools-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
            gap: 12px;
        }

        .tool-card {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 16px;
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            text-decoration: none;
            color: var(--text-primary);
            transition: all 0.2s;
        }

        .tool-card:hover {
            border-color: var(--accent);
            transform: translateY(-2px);
            box-shadow: var(--shadow);
        }

        .tool-icon {
            width: 40px;
            height: 40px;
            border-radius: var(--radius-sm);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
        }

        .tool-info h3 {
            font-size: 0.9rem;
            font-weight: 600;
            margin-bottom: 2px;
        }

        .tool-info span {
            font-size: 0.8rem;
            color: var(--text-muted);
        }

        /* Sessions Table */
        .sessions-container {
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            overflow: hidden;
        }

        .sessions-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 16px 20px;
            border-bottom: 1px solid var(--border);
            background: var(--bg-tertiary);
        }

        .sessions-header h2 {
            font-size: 1rem;
            font-weight: 600;
        }

        .sessions-list {
            max-height: 600px;
            overflow-y: auto;
        }

        .session-row {
            display: flex;
            align-items: center;
            padding: 16px 20px;
            border-bottom: 1px solid var(--border-subtle);
            transition: background 0.15s;
            cursor: pointer;
            text-decoration: none;
            color: inherit;
        }

        .session-row:hover {
            background: var(--bg-hover);
        }

        .session-row:last-child {
            border-bottom: none;
        }

        .session-tool {
            width: 36px;
            height: 36px;
            border-radius: var(--radius-sm);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
            margin-right: 16px;
            flex-shrink: 0;
        }

        .session-info {
            flex: 1;
            min-width: 0;
        }

        .session-title {
            font-weight: 500;
            margin-bottom: 4px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .session-meta {
            display: flex;
            gap: 16px;
            font-size: 0.8rem;
            color: var(--text-muted);
        }

        .session-messages {
            color: var(--text-muted);
            font-size: 0.85rem;
            flex-shrink: 0;
            margin-left: 16px;
        }

        /* Tool Badge */
        .tool-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 500;
        }

        /* Filter Bar */
        .filter-bar {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
            margin-bottom: 24px;
            padding: 16px;
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: var(--radius);
        }

        .filter-bar select,
        .filter-bar input {
            padding: 10px 14px;
            background: var(--bg-tertiary);
            border: 1px solid var(--border);
            border-radius: var(--radius-sm);
            color: var(--text-primary);
            font-family: inherit;
            font-size: 0.9rem;
            transition: border-color 0.2s;
        }

        .filter-bar select:focus,
        .filter-bar input:focus {
            outline: none;
            border-color: var(--accent);
        }

        .filter-bar input {
            flex: 1;
            min-width: 200px;
        }

        .btn {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 10px 20px;
            background: var(--accent);
            color: white;
            border: none;
            border-radius: var(--radius-sm);
            font-family: inherit;
            font-size: 0.9rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
        }

        .btn:hover {
            background: var(--accent-hover);
            transform: translateY(-1px);
        }

        .btn-secondary {
            background: var(--bg-tertiary);
            border: 1px solid var(--border);
            color: var(--text-primary);
        }

        .btn-secondary:hover {
            background: var(--bg-hover);
            border-color: var(--text-muted);
        }

        /* Session Detail */
        .session-detail {
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            overflow: hidden;
        }

        .session-detail-header {
            padding: 24px;
            border-bottom: 1px solid var(--border);
            background: var(--bg-tertiary);
        }

        .session-detail-header h1 {
            font-size: 1.5rem;
            margin-bottom: 16px;
        }

        .session-meta-grid {
            display: flex;
            flex-wrap: wrap;
            gap: 24px;
        }

        .meta-item {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }

        .meta-label {
            font-size: 0.75rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .meta-value {
            font-weight: 500;
        }

        /* Conversation */
        .conversation {
            padding: 24px;
        }

        .message {
            margin-bottom: 24px;
            padding: 20px;
            border-radius: var(--radius);
            animation: fadeIn 0.3s ease-out;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .message.user {
            background: var(--accent-subtle);
            border-left: 3px solid var(--accent);
        }

        .message.assistant {
            background: var(--bg-tertiary);
            border-left: 3px solid var(--success);
        }

        .message-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
            padding-bottom: 12px;
            border-bottom: 1px solid var(--border-subtle);
        }

        .message-role {
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .message-role.user { color: var(--accent); }
        .message-role.assistant { color: var(--success); }

        .message-time {
            font-size: 0.8rem;
            color: var(--text-muted);
            font-family: 'JetBrains Mono', monospace;
        }

        .message-content {
            font-size: 0.95rem;
            line-height: 1.7;
        }

        .message-content p { margin-bottom: 12px; }
        .message-content p:last-child { margin-bottom: 0; }

        .message-content pre {
            background: var(--bg-primary);
            border: 1px solid var(--border);
            border-radius: var(--radius-sm);
            padding: 16px;
            overflow-x: auto;
            margin: 12px 0;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.85rem;
        }

        .message-content code {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.85em;
            background: var(--bg-elevated);
            padding: 2px 6px;
            border-radius: 4px;
        }

        .message-content pre code {
            background: none;
            padding: 0;
        }

        .tool-call {
            background: var(--bg-elevated);
            border: 1px solid var(--border);
            border-radius: var(--radius-sm);
            padding: 12px 16px;
            margin: 12px 0;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.85rem;
        }

        .tool-call-header {
            display: flex;
            align-items: center;
            gap: 8px;
            color: var(--warning);
            font-weight: 500;
            margin-bottom: 8px;
        }

        /* Search Modal */
        .search-modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.7);
            backdrop-filter: blur(4px);
            z-index: 1000;
            align-items: flex-start;
            justify-content: center;
            padding-top: 15vh;
        }

        .search-modal.active {
            display: flex;
        }

        .search-box {
            width: 100%;
            max-width: 600px;
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            box-shadow: var(--shadow-lg);
            overflow: hidden;
        }

        .search-input-wrapper {
            display: flex;
            align-items: center;
            padding: 16px 20px;
            border-bottom: 1px solid var(--border);
        }

        .search-input-wrapper svg {
            width: 20px;
            height: 20px;
            color: var(--text-muted);
            margin-right: 12px;
        }

        .search-input {
            flex: 1;
            background: none;
            border: none;
            color: var(--text-primary);
            font-size: 1.1rem;
            font-family: inherit;
        }

        .search-input:focus { outline: none; }
        .search-input::placeholder { color: var(--text-muted); }

        .search-results {
            max-height: 400px;
            overflow-y: auto;
        }

        .search-result {
            display: flex;
            align-items: center;
            padding: 12px 20px;
            cursor: pointer;
            transition: background 0.15s;
        }

        .search-result:hover {
            background: var(--bg-hover);
        }

        .search-hint {
            padding: 16px 20px;
            color: var(--text-muted);
            font-size: 0.85rem;
            text-align: center;
        }

        /* Pagination */
        .pagination {
            display: flex;
            justify-content: center;
            gap: 8px;
            margin-top: 24px;
        }

        .pagination a {
            padding: 8px 16px;
            background: var(--bg-tertiary);
            border: 1px solid var(--border);
            border-radius: var(--radius-sm);
            color: var(--text-primary);
            text-decoration: none;
            transition: all 0.2s;
        }

        .pagination a:hover {
            border-color: var(--accent);
        }

        .pagination a.active {
            background: var(--accent);
            border-color: var(--accent);
        }

        /* Empty State */
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: var(--text-muted);
            animation: fadeIn 0.5s ease-out;
        }

        .empty-state svg {
            width: 80px;
            height: 80px;
            margin-bottom: 20px;
            opacity: 0.4;
            color: var(--text-muted);
            animation: float 3s ease-in-out infinite;
        }

        @keyframes float {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-10px); }
        }

        .empty-state h2 {
            color: var(--text-secondary);
            margin-bottom: 12px;
            font-size: 1.5rem;
        }

        .empty-state p {
            color: var(--text-muted);
            font-size: 1rem;
            max-width: 400px;
            margin: 0 auto;
        }

        .empty-state code {
            background: var(--bg-tertiary);
            padding: 4px 10px;
            border-radius: 6px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.9rem;
            color: var(--accent);
            border: 1px solid var(--border-subtle);
        }

        .empty-state-btn {
            margin-top: 24px;
            padding: 12px 24px;
            background: var(--accent);
            color: white;
            border: none;
            border-radius: var(--radius-sm);
            font-size: 0.95rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
        }

        .empty-state-btn:hover {
            background: var(--accent-hover);
            transform: translateY(-2px);
            box-shadow: var(--shadow);
        }

        /* Back Link */
        .back-link {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            color: var(--text-muted);
            text-decoration: none;
            font-size: 0.9rem;
            margin-bottom: 24px;
            transition: color 0.2s;
        }

        .back-link:hover { color: var(--accent); }

        /* View All Link */
        .view-all {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            color: var(--accent);
            text-decoration: none;
            font-size: 0.9rem;
            font-weight: 500;
            transition: all 0.2s;
        }

        .view-all:hover {
            color: var(--accent-hover);
            gap: 12px;
        }

        /* Theme Toggle Button */
        .theme-toggle {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 36px;
            height: 36px;
            background: var(--bg-tertiary);
            border: 1px solid var(--border);
            border-radius: var(--radius-sm);
            color: var(--text-secondary);
            cursor: pointer;
            transition: all 0.2s;
        }

        .theme-toggle:hover {
            border-color: var(--text-muted);
            color: var(--text-primary);
        }

        /* Mobile Menu Toggle */
        .mobile-menu-toggle {
            display: none;
            align-items: center;
            justify-content: center;
            width: 36px;
            height: 36px;
            background: var(--bg-tertiary);
            border: 1px solid var(--border);
            border-radius: var(--radius-sm);
            color: var(--text-secondary);
            cursor: pointer;
            transition: all 0.2s;
        }

        .mobile-menu-toggle:hover {
            border-color: var(--text-muted);
            color: var(--text-primary);
        }

        /* Mobile Nav */
        .mobile-nav {
            display: none;
            position: fixed;
            top: 60px;
            left: 0;
            right: 0;
            background: var(--bg-secondary);
            border-bottom: 1px solid var(--border);
            padding: 16px;
            z-index: 99;
        }

        .mobile-nav.active {
            display: block;
        }

        .mobile-nav a {
            display: block;
            padding: 12px 16px;
            color: var(--text-primary);
            text-decoration: none;
            border-radius: var(--radius-sm);
            margin-bottom: 4px;
        }

        .mobile-nav a:hover {
            background: var(--bg-hover);
        }

        .mobile-nav a.active {
            background: var(--bg-tertiary);
            color: var(--accent);
        }

        /* Loading Spinner */
        .spinner {
            width: 40px;
            height: 40px;
            border: 3px solid var(--border);
            border-top-color: var(--accent);
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            margin: 0 auto;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        /* Loading Overlay */
        .loading-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: var(--bg-primary);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1000;
        }

        /* Loading Button State */
        .btn.loading {
            opacity: 0.7;
            pointer-events: none;
            position: relative;
        }

        .btn.loading::after {
            content: "";
            position: absolute;
            width: 16px;
            height: 16px;
            border: 2px solid transparent;
            border-top-color: white;
            border-radius: 50%;
            animation: spin 0.6s linear infinite;
            right: 20px;
        }

        /* Toast Notification */
        .toast {
            position: fixed;
            bottom: 24px;
            right: 24px;
            padding: 12px 20px;
            background: var(--bg-elevated);
            border: 1px solid var(--border);
            border-radius: var(--radius-sm);
            box-shadow: var(--shadow-lg);
            display: flex;
            align-items: center;
            gap: 10px;
            z-index: 1001;
            transform: translateY(100px);
            opacity: 0;
            transition: all 0.3s ease-out;
        }

        .toast.show {
            transform: translateY(0);
            opacity: 1;
        }

        .toast.success { border-color: var(--success); }
        .toast.error { border-color: var(--error); }

        /* Responsive */
        @media (max-width: 768px) {
            .mobile-menu-toggle { display: flex; }
            .desktop-nav { display: none; }
            .header-inner { padding: 12px 16px; }
            main { padding: 20px 16px; }
            .stats-grid { grid-template-columns: repeat(2, 1fr); }
            .tools-grid { grid-template-columns: repeat(2, 1fr); }
            .filter-bar { flex-direction: column; }
            .filter-bar input { min-width: 100%; }
            .session-row { flex-wrap: wrap; }
            .session-messages { width: 100%; margin-left: 52px; margin-top: 8px; }
            .search-trigger span.kbd { display: none; }
            .toast { left: 16px; right: 16px; bottom: 16px; }
        }
    </style>
</head>
<body>
    <header>
        <div class="header-inner">
            <a href="/" class="logo">
                <div class="logo-icon">📚</div>
                <span>ai-history</span>
            </a>
            <nav class="desktop-nav">
                <a href="/" class="{{ 'active' if active == 'dashboard' else '' }}">Dashboard</a>
                <a href="/sessions" class="{{ 'active' if active == 'sessions' else '' }}">Sessions</a>
                <a href="/settings" class="{{ 'active' if active == 'settings' else '' }}">Settings</a>
                <button class="search-trigger" onclick="openSearch()">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="11" cy="11" r="8"></circle>
                        <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                    </svg>
                    Search...
                    <span class="kbd">⌘K</span>
                </button>
                <button class="theme-toggle" onclick="toggleTheme()" aria-label="Toggle dark mode" title="Toggle theme">
                    <span id="themeIcon">🌙</span>
                </button>
            </nav>
            <button class="mobile-menu-toggle" onclick="toggleMobileMenu()" aria-label="Toggle menu" title="Toggle menu">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="3" y1="12" x2="21" y2="12"></line>
                    <line x1="3" y1="6" x2="21" y2="6"></line>
                    <line x1="3" y1="18" x2="21" y2="18"></line>
                </svg>
            </button>
        </div>
        <div class="mobile-nav" id="mobileNav">
            <a href="/" onclick="closeMobileMenu()">Dashboard</a>
            <a href="/sessions" onclick="closeMobileMenu()">Sessions</a>
            <a href="/settings" onclick="closeMobileMenu()">Settings</a>
            <button class="search-trigger" onclick="openSearch(); closeMobileMenu();" style="width: 100%; text-align: left;">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="11" cy="11" r="8"></circle>
                    <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                </svg>
                Search
            </button>
            <button class="theme-toggle" onclick="toggleTheme()" style="width: 100%; margin-top: 8px;">
                <span id="themeIconMobile">🌙</span> Toggle Theme
            </button>
        </div>
    </header>

    <main>
        {% block content %}{% endblock %}
    </main>

    <!-- Search Modal -->
    <div class="search-modal" id="searchModal">
        <div class="search-box">
            <div class="search-input-wrapper">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="11" cy="11" r="8"></circle>
                    <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                </svg>
                <input type="text" class="search-input" id="searchInput" placeholder="Search conversations..." autocomplete="off">
            </div>
            <div class="search-results" id="searchResults">
                <div class="search-hint">Type to search across all your AI conversations</div>
            </div>
        </div>
    </div>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    <script>
        // Initialize syntax highlighting
        document.addEventListener('DOMContentLoaded', () => {
            document.querySelectorAll('pre code').forEach(block => {
                hljs.highlightElement(block);
            });
        });

        // Search Modal
        function openSearch() {
            document.getElementById('searchModal').classList.add('active');
            document.getElementById('searchInput').focus();
        }

        function closeSearch() {
            document.getElementById('searchModal').classList.remove('active');
            document.getElementById('searchInput').value = '';
            document.getElementById('searchResults').innerHTML = '<div class="search-hint">Type to search across all your AI conversations</div>';
        }

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            // Cmd/Ctrl + K to open search
            if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
                e.preventDefault();
                openSearch();
            }
            // Escape to close search
            if (e.key === 'Escape') {
                closeSearch();
            }
            // G then D for dashboard
            if (e.key === 'g' && !e.metaKey && !e.ctrlKey && document.activeElement.tagName !== 'INPUT') {
                window._gPressed = true;
                setTimeout(() => { window._gPressed = false; }, 500);
            }
            if (e.key === 'd' && window._gPressed && document.activeElement.tagName !== 'INPUT') {
                window.location.href = '/';
            }
        });

        // Click outside to close
        document.getElementById('searchModal').addEventListener('click', (e) => {
            if (e.target.id === 'searchModal') closeSearch();
        });

        // Live search
        let searchTimeout;
        document.getElementById('searchInput').addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            const query = e.target.value.trim();

            if (query.length < 2) {
                document.getElementById('searchResults').innerHTML = '<div class="search-hint">Type to search across all your AI conversations</div>';
                return;
            }

            searchTimeout = setTimeout(() => {
                fetch(`/api/search?q=${encodeURIComponent(query)}`)
                    .then(r => r.json())
                    .then(results => {
                        if (results.length === 0) {
                            document.getElementById('searchResults').innerHTML = '<div class="search-hint">No results found</div>';
                            return;
                        }

                        const html = results.slice(0, 10).map(r => `
                            <a href="/session/${r.id}" class="search-result">
                                <div class="session-tool" style="background: ${r.bg || '#2d3748'}">
                                    ${r.icon || '🤖'}
                                </div>
                                <div class="session-info">
                                    <div class="session-title">${r.title || r.id.slice(0, 20)}</div>
                                    <div class="session-meta">
                                        <span>${r.tool}</span>
                                        <span>${r.date}</span>
                                    </div>
                                </div>
                            </a>
                        `).join('');

                        document.getElementById('searchResults').innerHTML = html;
                    });
            }, 200);
        });

        // Theme Toggle
        function toggleTheme() {
            const html = document.documentElement;
            const currentTheme = html.getAttribute('data-theme') || 'dark';
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            html.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            updateThemeIcons(newTheme);
        }

        function updateThemeIcons(theme) {
            const icons = {
                dark: '🌙',
                light: '☀️'
            };
            const iconElements = ['themeIcon', 'themeIconMobile'];
            iconElements.forEach(id => {
                const el = document.getElementById(id);
                if (el) el.textContent = icons[theme] || icons.dark;
            });
        }

        // Load saved theme
        (function loadSavedTheme() {
            const savedTheme = localStorage.getItem('theme');
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            const theme = savedTheme || (prefersDark ? 'dark' : 'light');
            document.documentElement.setAttribute('data-theme', theme);
            updateThemeIcons(theme);
        })();

        // Mobile Menu
        function toggleMobileMenu() {
            document.getElementById('mobileNav').classList.toggle('active');
        }

        function closeMobileMenu() {
            document.getElementById('mobileNav').classList.remove('active');
        }

        // Toast Notification
        function showToast(message, type = 'success') {
            const existing = document.querySelector('.toast');
            if (existing) existing.remove();

            const toast = document.createElement('div');
            toast.className = `toast ${type}`;
            toast.innerHTML = `
                <span>${type === 'success' ? '✓' : '✗'}</span>
                <span>${message}</span>
            `;
            document.body.appendChild(toast);

            requestAnimationFrame(() => toast.classList.add('show'));
            setTimeout(() => {
                toast.classList.remove('show');
                setTimeout(() => toast.remove(), 300);
            }, 3000);
        }
    </script>
</body>
</html>
"""

DASHBOARD_TEMPLATE = """
{% extends "base" %}
{% block content %}
<div class="page-header">
    <h1>Dashboard</h1>
    <p>Your AI conversation history across all tools</p>
</div>

<div class="stats-grid">
    <div class="stat-card">
        <div class="stat-label">Total Sessions</div>
        <div class="stat-value">{{ "{:,}".format(stats.total_sessions) }}</div>
    </div>
    <div class="stat-card">
        <div class="stat-label">Total Messages</div>
        <div class="stat-value">{{ "{:,}".format(stats.total_messages) }}</div>
    </div>
    <div class="stat-card">
        <div class="stat-label">AI Tools</div>
        <div class="stat-value">{{ stats.by_tool | length }}</div>
    </div>
    <div class="stat-card">
        <div class="stat-label">Projects</div>
        <div class="stat-value">{{ stats.by_project | length }}</div>
    </div>
</div>

<div class="tools-section">
    <div class="section-header">
        <h2 class="section-title">Sessions by Tool</h2>
    </div>
    <div class="tools-grid">
        {% for tool, count in stats.by_tool.items() %}
        <a href="/sessions?tool={{ tool }}" class="tool-card">
            <div class="tool-icon" style="background: {{ tool_styles.get(tool, {}).get('bg', '#2d3748') }}">
                {{ tool_styles.get(tool, {}).get('icon', '🤖') }}
            </div>
            <div class="tool-info">
                <h3>{{ tool }}</h3>
                <span>{{ count }} sessions</span>
            </div>
        </a>
        {% endfor %}
    </div>
</div>

<div class="tools-section">
    <div class="section-header">
        <h2 class="section-title">Recent Sessions</h2>
        <a href="/sessions" class="view-all">View all →</a>
    </div>
    <div class="sessions-container">
        <div class="sessions-list">
            {% for session in recent_sessions %}
            <a href="/session/{{ session.id }}" class="session-row">
                <div class="session-tool" style="background: {{ tool_styles.get(session.tool, {}).get('bg', '#2d3748') }}">
                    {{ tool_styles.get(session.tool, {}).get('icon', '🤖') }}
                </div>
                <div class="session-info">
                    <div class="session-title">{{ session.title or session.project or session.id[:20] }}</div>
                    <div class="session-meta">
                        <span>{{ session.tool }}</span>
                        <span>{{ session.created[:10] }}</span>
                        {% if session.project %}<span>{{ session.project | truncate(40) }}</span>{% endif %}
                    </div>
                </div>
                <div class="session-messages">{{ session.messages }} messages</div>
            </a>
            {% endfor %}
        </div>
    </div>
</div>
{% endblock %}
"""

SESSIONS_TEMPLATE = """
{% extends "base" %}
{% block content %}
<div class="page-header">
    <h1>Sessions</h1>
    <p>Browse and filter your AI conversations</p>
</div>

<div class="filter-bar">
    <form method="GET" style="display: flex; gap: 12px; flex-wrap: wrap; width: 100%;">
        <select name="tool">
            <option value="">All Tools</option>
            {% for t in tools %}
            <option value="{{ t }}" {{ 'selected' if tool == t else '' }}>{{ t }}</option>
            {% endfor %}
        </select>
        <input type="text" name="project" placeholder="Filter by project path..." value="{{ project or '' }}">
        <select name="since">
            <option value="">All Time</option>
            <option value="1d" {{ 'selected' if since == '1d' else '' }}>Last 24 hours</option>
            <option value="7d" {{ 'selected' if since == '7d' else '' }}>Last 7 days</option>
            <option value="30d" {{ 'selected' if since == '30d' else '' }}>Last 30 days</option>
            <option value="90d" {{ 'selected' if since == '90d' else '' }}>Last 3 months</option>
        </select>
        <button type="submit" class="btn">Apply Filters</button>
        {% if tool or project or since %}
        <a href="/sessions" class="btn btn-secondary">Clear</a>
        {% endif %}
    </form>
</div>

{% if sessions %}
<div class="sessions-container">
    <div class="sessions-header">
        <h2>{{ total }} sessions found</h2>
    </div>
    <div class="sessions-list">
        {% for session in sessions %}
        <a href="/session/{{ session.id }}" class="session-row">
            <div class="session-tool" style="background: {{ tool_styles.get(session.tool, {}).get('bg', '#2d3748') }}">
                {{ tool_styles.get(session.tool, {}).get('icon', '🤖') }}
            </div>
            <div class="session-info">
                <div class="session-title">{{ session.title or session.project or session.id[:20] }}</div>
                <div class="session-meta">
                    <span>{{ session.tool }}</span>
                    <span>{{ session.created[:10] }}</span>
                    {% if session.project %}<span>{{ session.project | truncate(50) }}</span>{% endif %}
                </div>
            </div>
            <div class="session-messages">{{ session.messages }} msg</div>
        </a>
        {% endfor %}
    </div>
</div>

{% if total > per_page %}
<div class="pagination">
    {% if page > 1 %}
    <a href="?page={{ page - 1 }}&tool={{ tool or '' }}&project={{ project or '' }}&since={{ since or '' }}">← Previous</a>
    {% endif %}

    {% for p in range(1, (total // per_page) + 2) %}
        {% if p <= 5 or p > (total // per_page) - 2 or (p >= page - 1 and p <= page + 1) %}
            <a href="?page={{ p }}&tool={{ tool or '' }}&project={{ project or '' }}&since={{ since or '' }}" class="{{ 'active' if p == page else '' }}">{{ p }}</a>
        {% elif p == 6 or p == (total // per_page) - 2 %}
            <span style="color: var(--text-muted)">...</span>
        {% endif %}
    {% endfor %}

    {% if page * per_page < total %}
    <a href="?page={{ page + 1 }}&tool={{ tool or '' }}&project={{ project or '' }}&since={{ since or '' }}">Next →</a>
    {% endif %}
</div>
{% endif %}

{% else %}
<div class="empty-state">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/>
    </svg>
    <h2>No sessions found</h2>
    <p>Try adjusting your filters or run <code>ai-history export --all</code> first.</p>
    <button class="empty-state-btn" onclick="window.location.href='/'">Go to Dashboard</button>
</div>
{% endif %}
{% endblock %}
"""

SESSION_TEMPLATE = """
{% extends "base" %}
{% block content %}
<a href="/sessions" class="back-link">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M19 12H5M12 19l-7-7 7-7"/>
    </svg>
    Back to Sessions
</a>

<div class="session-layout">
    <!-- Left Sidebar: Table of Contents -->
    <aside class="session-toc">
        <div class="toc-header">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="8" y1="6" x2="21" y2="6"></line>
                <line x1="8" y1="12" x2="21" y2="12"></line>
                <line x1="8" y1="18" x2="21" y2="18"></line>
                <line x1="3" y1="6" x2="3.01" y2="6"></line>
                <line x1="3" y1="12" x2="3.01" y2="12"></line>
                <line x1="3" y1="18" x2="3.01" y2="18"></line>
            </svg>
            On this page
        </div>
        <nav class="toc-list">
            {% for item in toc_items %}
            <a href="#msg-{{ item.index }}" class="toc-item">
                <span class="toc-number">{{ item.index + 1 }}</span>
                <span class="toc-text">{{ item.text }}</span>
            </a>
            {% endfor %}

            <div class="toc-footer">
                {{ toc_items | length }} prompts
            </div>
        </nav>
    </aside>

    <!-- Main Content -->
    <div class="session-detail">
        <div class="session-detail-header">
            <h1>{{ session.title or 'Session ' + session.session_id[:8] }}</h1>
            <div class="session-meta-grid">
                <div class="meta-item">
                    <span class="meta-label">Tool</span>
                    <span class="meta-value">
                        <span class="tool-badge" style="background: {{ tool_styles.get(session.tool.value, {}).get('bg', '#2d3748') }}; color: {{ tool_styles.get(session.tool.value, {}).get('color', '#a0aec0') }}">
                            {{ tool_styles.get(session.tool.value, {}).get('icon', '🤖') }} {{ session.tool.value }}
                        </span>
                    </span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Date</span>
                    <span class="meta-value">{{ session.created_at.strftime('%B %d, %Y at %H:%M') }}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Messages</span>
                    <span class="meta-value">{{ session.message_count }}</span>
                </div>
                {% if session.project_path %}
                <div class="meta-item">
                    <span class="meta-label">Project</span>
                    <span class="meta-value" style="font-family: 'JetBrains Mono', monospace; font-size: 0.85rem;">{{ session.project_path }}</span>
                </div>
                {% endif %}
            </div>
        </div>

        <div class="conversation">
            {% if md_only %}
            <div class="md-content">{{ session.md_content | safe }}</div>
            {% else %}
            {% set ns = namespace(user_index=0) %}
            {% for msg in session.messages %}
            {# Only show messages with content #}
            {% if msg.content and msg.content|striptags|trim %}
            <div class="message {{ msg.role.value }}" {% if msg.role.value == 'user' %}id="msg-{{ ns.user_index }}"{% endif %}>
                <div class="message-header">
                    <span class="message-role {{ msg.role.value }}">
                        {% if msg.role.value == 'user' %}👤{% else %}🤖{% endif %}
                        {{ msg.role.value | title }}
                    </span>
                    <span class="message-time">{{ msg.timestamp.strftime('%H:%M:%S') }}</span>
                </div>
                <div class="message-content">{{ msg.content | safe }}</div>
            </div>
            {% endif %}
            {% if msg.role.value == 'user' %}
                {% set ns.user_index = ns.user_index + 1 %}
            {% endif %}
            {% endfor %}
            {% endif %}
    </div>
</div>

<style>
    .session-layout {
        display: grid;
        grid-template-columns: 280px 1fr;
        gap: 32px;
        align-items: start;
    }

    .session-toc {
        position: sticky;
        top: 80px;
        background: var(--bg-secondary);
        border: 1px solid var(--border);
        border-radius: var(--radius);
        padding: 20px;
        max-height: calc(100vh - 120px);
        overflow-y: auto;
    }

    .toc-header {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--text-muted);
        margin-bottom: 16px;
        padding-bottom: 12px;
        border-bottom: 1px solid var(--border);
    }

    .toc-header svg {
        width: 14px;
        height: 14px;
    }

    .toc-list {
        display: flex;
        flex-direction: column;
        gap: 4px;
    }

    .toc-item {
        display: flex;
        align-items: start;
        gap: 10px;
        padding: 8px 10px;
        border-radius: 6px;
        text-decoration: none;
        color: var(--text-secondary);
        font-size: 0.85rem;
        line-height: 1.4;
        transition: all 0.2s;
    }

    .toc-item:hover {
        background: var(--bg-hover);
        color: var(--text-primary);
    }

    .toc-item.active {
        background: var(--accent-subtle);
        color: var(--accent);
    }

    .toc-number {
        flex-shrink: 0;
        width: 20px;
        height: 20px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: var(--bg-tertiary);
        border-radius: 50%;
        font-size: 0.75rem;
        font-weight: 600;
        color: var(--text-muted);
    }

    .toc-item:hover .toc-number {
        background: var(--accent);
        color: white;
    }

    .toc-text {
        flex: 1;
        overflow: hidden;
        text-overflow: ellipsis;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
    }

    .toc-footer {
        margin-top: 16px;
        padding-top: 12px;
        border-top: 1px solid var(--border);
        font-size: 0.75rem;
        color: var(--text-muted);
        text-align: center;
    }

    /* Scroll margin for anchor links */
    .message[id] {
        scroll-margin-top: 100px;
    }

    /* Responsive */
    @media (max-width: 1024px) {
        .session-layout {
            grid-template-columns: 1fr;
        }

        .session-toc {
            position: relative;
            top: 0;
            max-height: 400px;
        }
    }
</style>

<script>
    // Highlight active TOC item on scroll
    document.addEventListener('DOMContentLoaded', () => {
        const tocItems = document.querySelectorAll('.toc-item');
        const messages = document.querySelectorAll('.message[id]');

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const id = entry.target.id;
                    tocItems.forEach(item => {
                        if (item.getAttribute('href') === `#${id}`) {
                            item.classList.add('active');
                        } else {
                            item.classList.remove('active');
                        }
                    });
                }
            });
        }, { rootMargin: '-100px 0px -80% 0px' });

        messages.forEach(msg => observer.observe(msg));
    });
</script>
{% endblock %}
"""

SETTINGS_TEMPLATE = """
{% extends "base" %}
{% block content %}
<div class="page-header">
    <h1>Settings</h1>
    <p>Configure sync, integrations, and preferences</p>
</div>

<div class="settings-grid">
    <!-- Cloud Sync Section -->
    <div class="settings-card">
        <div class="settings-card-header">
            <div class="settings-icon" style="background: var(--accent-subtle);">☁️</div>
            <div>
                <h2>Cloud Sync</h2>
                <p>Backup your AI history to the cloud</p>
            </div>
        </div>
        <div class="settings-card-body">
            <div class="sync-status">
                {% if sync_status.remote_configured %}
                <div class="status-badge success">
                    <span class="status-dot"></span>
                    Connected to {{ sync_status.remote_name }}
                </div>
                {% else %}
                <div class="status-badge warning">
                    <span class="status-dot"></span>
                    Not configured
                </div>
                {% endif %}
            </div>

            {% if sync_status.remote_configured %}
            <div class="sync-info">
                {% if sync_status.last_sync %}
                <div class="info-row">
                    <span>Last sync:</span>
                    <span>{{ sync_status.last_sync[:19] }}</span>
                </div>
                {% endif %}
                {% if sync_status.remote_size %}
                <div class="info-row">
                    <span>Cloud storage:</span>
                    <span>{{ sync_status.remote_files }} files ({{ sync_status.remote_size }})</span>
                </div>
                {% endif %}
            </div>

            <div class="sync-actions">
                <form action="/api/sync/push" method="POST" style="display: inline;">
                    <button type="submit" class="btn">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M12 19V5M5 12l7-7 7 7"/>
                        </svg>
                        Push to Cloud
                    </button>
                </form>
                <form action="/api/sync/pull" method="POST" style="display: inline;">
                    <button type="submit" class="btn btn-secondary">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M12 5v14M5 12l7 7 7-7"/>
                        </svg>
                        Pull from Cloud
                    </button>
                </form>
            </div>
            {% else %}
            <div class="setup-instructions">
                <p>To enable cloud sync, run in terminal:</p>
                <pre><code>cd ~/projects/mcp-server/ai-history
python3 sync.py --setup gdrive</code></pre>
            </div>
            {% endif %}
        </div>
    </div>

    <!-- Detected Tools Section -->
    <div class="settings-card">
        <div class="settings-card-header">
            <div class="settings-icon" style="background: var(--success-subtle);">🔌</div>
            <div>
                <h2>Connected Tools</h2>
                <p>AI tools with detected chat history</p>
            </div>
        </div>
        <div class="settings-card-body">
            <div class="tools-list">
                {% for tool in detected_tools %}
                <div class="tool-item">
                    <div class="tool-item-icon" style="background: {{ tool_styles.get(tool.name, {}).get('bg', '#2d3748') }}">
                        {{ tool_styles.get(tool.name, {}).get('icon', '🤖') }}
                    </div>
                    <div class="tool-item-info">
                        <span class="tool-item-name">{{ tool.name }}</span>
                        <span class="tool-item-path">{{ tool.path }}</span>
                    </div>
                    <div class="tool-item-status {{ 'active' if tool.available else 'inactive' }}">
                        {{ '✓' if tool.available else '✗' }}
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
    </div>

    <!-- Data Management Section -->
    <div class="settings-card">
        <div class="settings-card-header">
            <div class="settings-icon" style="background: var(--warning)20;">📊</div>
            <div>
                <h2>Data Management</h2>
                <p>Export, rebuild index, and manage storage</p>
            </div>
        </div>
        <div class="settings-card-body">
            <div class="data-actions">
                <form action="/api/rebuild-index" method="POST">
                    <button type="submit" class="btn btn-secondary" style="width: 100%; margin-bottom: 12px;">
                        🔄 Rebuild Index
                    </button>
                </form>
                <a href="/export-all" class="btn btn-secondary" style="width: 100%; text-align: center; display: block; margin-bottom: 12px;">
                    📥 Export All Sessions
                </a>
                <div class="info-row">
                    <span>Index location:</span>
                    <code style="font-size: 0.75rem;">~/.ai-history/index.json</code>
                </div>
            </div>
        </div>
    </div>

    <!-- About Section -->
    <div class="settings-card">
        <div class="settings-card-header">
            <div class="settings-icon" style="background: #8b5cf620;">ℹ️</div>
            <div>
                <h2>About ai-history</h2>
                <p>Local-first AI chat history manager</p>
            </div>
        </div>
        <div class="settings-card-body">
            <div class="about-info">
                <p>A privacy-focused alternative to SpecStory that keeps your AI conversations local.</p>
                <div class="info-row" style="margin-top: 16px;">
                    <span>Version:</span>
                    <span>2.0.0</span>
                </div>
                <div class="info-row">
                    <span>Supported tools:</span>
                    <span>7</span>
                </div>
                <div class="info-row">
                    <span>Storage:</span>
                    <span>~/.ai-history/</span>
                </div>
            </div>
        </div>
    </div>
</div>

<style>
    .settings-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
        gap: 24px;
    }

    .settings-card {
        background: var(--bg-secondary);
        border: 1px solid var(--border);
        border-radius: var(--radius);
        overflow: hidden;
    }

    .settings-card-header {
        display: flex;
        align-items: center;
        gap: 16px;
        padding: 20px;
        border-bottom: 1px solid var(--border);
        background: var(--bg-tertiary);
    }

    .settings-icon {
        width: 48px;
        height: 48px;
        border-radius: var(--radius-sm);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 24px;
    }

    .settings-card-header h2 {
        font-size: 1.1rem;
        font-weight: 600;
        margin-bottom: 4px;
    }

    .settings-card-header p {
        font-size: 0.85rem;
        color: var(--text-muted);
    }

    .settings-card-body {
        padding: 20px;
    }

    .sync-status {
        margin-bottom: 16px;
    }

    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 6px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 500;
    }

    .status-badge.success {
        background: var(--success-subtle);
        color: var(--success);
    }

    .status-badge.warning {
        background: var(--warning)20;
        color: var(--warning);
    }

    .status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: currentColor;
    }

    .sync-info, .sync-actions {
        margin-top: 16px;
    }

    .sync-actions {
        display: flex;
        gap: 12px;
        flex-wrap: wrap;
    }

    .info-row {
        display: flex;
        justify-content: space-between;
        padding: 8px 0;
        border-bottom: 1px solid var(--border-subtle);
        font-size: 0.9rem;
    }

    .info-row:last-child {
        border-bottom: none;
    }

    .info-row span:first-child {
        color: var(--text-muted);
    }

    .setup-instructions {
        background: var(--bg-tertiary);
        border-radius: var(--radius-sm);
        padding: 16px;
    }

    .setup-instructions p {
        margin-bottom: 12px;
        color: var(--text-secondary);
    }

    .setup-instructions pre {
        background: var(--bg-primary);
        padding: 12px;
        border-radius: 6px;
        overflow-x: auto;
    }

    .setup-instructions code {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.85rem;
    }

    .tools-list {
        display: flex;
        flex-direction: column;
        gap: 8px;
    }

    .tool-item {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px;
        background: var(--bg-tertiary);
        border-radius: var(--radius-sm);
    }

    .tool-item-icon {
        width: 32px;
        height: 32px;
        border-radius: 6px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 16px;
    }

    .tool-item-info {
        flex: 1;
        min-width: 0;
    }

    .tool-item-name {
        display: block;
        font-weight: 500;
        font-size: 0.9rem;
    }

    .tool-item-path {
        display: block;
        font-size: 0.75rem;
        color: var(--text-muted);
        font-family: 'JetBrains Mono', monospace;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .tool-item-status {
        width: 24px;
        height: 24px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 12px;
    }

    .tool-item-status.active {
        background: var(--success-subtle);
        color: var(--success);
    }

    .tool-item-status.inactive {
        background: var(--error)20;
        color: var(--error);
    }

    .about-info p {
        color: var(--text-secondary);
        line-height: 1.6;
    }

    @media (max-width: 900px) {
        .settings-grid {
            grid-template-columns: 1fr;
        }
    }
</style>
{% endblock %}
"""


# Helper functions
def clear_index_cache():
    """Clear the cached index."""
    load_index.cache_clear()


@lru_cache(maxsize=1)
def load_index():
    """Load and cache the index file."""
    if not INDEX_PATH.exists():
        return {
            "stats": {
                "total_sessions": 0,
                "total_messages": 0,
                "by_tool": {},
                "by_project": {},
            },
            "sessions": [],
        }
    with open(INDEX_PATH, "r") as f:
        return json.load(f)


def get_tools():
    """Get list of available tools."""
    return list(TOOL_STYLES.keys())


def clean_text_for_toc(content):
    """Clean text for TOC display - remove HTML, markdown, truncate."""
    if not content:
        return ""

    import html
    import re

    # First, check if this is just a tool result marker
    if (
        content.strip() == "[Tool Result]"
        or content.strip().startswith("[Tool Result]")
        and len(content.strip()) < 20
    ):
        return ""

    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", content)

    # Remove tool markers and code blocks FIRST
    text = re.sub(
        r"\[Tool:.*?\].*?(?=\n\n|\Z)", "", text, flags=re.DOTALL
    )  # Remove [Tool: ...] blocks
    text = re.sub(r"```[\s\S]*?```", "", text)  # Remove code blocks
    text = re.sub(r"`[^`]+`", "", text)  # Remove inline code

    # Remove markdown formatting
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)  # Remove bold
    text = re.sub(r"\*([^*]+)\*", r"\1", text)  # Remove italic
    text = re.sub(r"#{1,6}\s+", "", text)  # Remove headers
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)  # Remove links

    # Remove extra whitespace and newlines
    text = " ".join(text.split())

    # Unescape HTML entities
    text = html.unescape(text)

    # Remove any remaining brackets
    text = re.sub(r"\[.*?\]", "", text)

    # Final cleanup
    text = text.strip()

    # If still empty or too short, return empty
    if not text or len(text) < 3:
        return ""

    # Truncate to 100 chars
    if len(text) > 100:
        text = text[:97] + "..."

    return text


def format_content(content):
    """Format message content with markdown and code highlighting."""
    if not content:
        return ""

    # Escape HTML but preserve code blocks
    import html

    # Extract code blocks first
    code_blocks = []

    def save_code_block(match):
        code_blocks.append(match.group(0))
        return f"__CODE_BLOCK_{len(code_blocks) - 1}__"

    content = re.sub(r"```[\s\S]*?```", save_code_block, content)

    # Escape HTML
    content = html.escape(content)

    # Restore code blocks with highlighting
    for i, block in enumerate(code_blocks):
        lang_match = re.match(r"```(\w+)?\n?([\s\S]*?)```", block)
        if lang_match:
            lang = lang_match.group(1) or ""
            code = html.escape(lang_match.group(2).strip())
            formatted = f'<pre><code class="language-{lang}">{code}</code></pre>'
        else:
            formatted = f"<pre><code>{html.escape(block)}</code></pre>"
        content = content.replace(f"__CODE_BLOCK_{i}__", formatted)

    # Format inline code
    content = re.sub(r"`([^`]+)`", r"<code>\1</code>", content)

    # Format tool calls
    content = re.sub(
        r"\[Tool: (\w+)\](.*?)(?=\n|$)",
        r'<div class="tool-call"><div class="tool-call-header">🔧 \1</div>\2</div>',
        content,
    )

    # Convert newlines to paragraphs
    paragraphs = content.split("\n\n")
    if len(paragraphs) > 1:
        content = "".join(f"<p>{p}</p>" for p in paragraphs if p.strip())
    else:
        content = content.replace("\n", "<br>")

    return content


def render(template_name, **kwargs):
    """Render a template with base template."""
    templates = {
        "base": BASE_TEMPLATE,
        "dashboard": DASHBOARD_TEMPLATE,
        "sessions": SESSIONS_TEMPLATE,
        "session": SESSION_TEMPLATE,
        "settings": SETTINGS_TEMPLATE,
    }

    from jinja2 import Environment, BaseLoader

    class TemplateLoader(BaseLoader):
        def get_source(self, environment, template):
            if template in templates:
                return templates[template], template, lambda: True
            raise Exception(f"Template not found: {template}")

    env = Environment(loader=TemplateLoader())
    env.filters["truncate"] = (
        lambda s, length: s[:length] + "..." if len(s) > length else s
    )
    template = env.get_template(template_name)
    return template.render(tool_styles=TOOL_STYLES, **kwargs)


# Routes
@app.route("/")
@requires_auth
def dashboard():
    clear_index_cache()
    index = load_index()
    stats = index.get("stats", {})
    sessions = sorted(
        index.get("sessions", []), key=lambda s: s.get("created", ""), reverse=True
    )[:15]

    return render(
        "dashboard",
        title="Dashboard",
        active="dashboard",
        stats=stats,
        recent_sessions=sessions,
    )


@app.route("/sessions")
@requires_auth
def sessions():
    clear_index_cache()
    index = load_index()
    all_sessions = index.get("sessions", [])

    tool = sanitize_input(request.args.get("tool", ""), max_length=50)
    project = sanitize_input(
        request.args.get("project", ""), max_length=200, allow_path_chars=True
    )
    since = sanitize_input(request.args.get("since", ""), max_length=10)

    try:
        page = max(1, min(int(request.args.get("page", 1)), 10000))
    except (ValueError, TypeError):
        page = 1

    per_page = 50

    # Apply filters
    filtered = all_sessions

    if tool:
        filtered = [s for s in filtered if s.get("tool") == tool]

    if project:
        filtered = [
            s for s in filtered if project.lower() in (s.get("project") or "").lower()
        ]

    if since:
        try:
            duration = ai_history.parse_duration(since)
            cutoff = datetime.now() - duration
            filtered = [
                s
                for s in filtered
                if s.get("created", "")[:10] >= cutoff.strftime("%Y-%m-%d")
            ]
        except ValueError:
            pass

    # Sort and paginate
    filtered = sorted(filtered, key=lambda s: s.get("created", ""), reverse=True)
    total = len(filtered)
    start = (page - 1) * per_page
    end = start + per_page
    paginated = filtered[start:end]

    return render(
        "sessions",
        title="Sessions",
        active="sessions",
        sessions=paginated,
        tools=get_tools(),
        tool=tool,
        project=project,
        since=since,
        page=page,
        per_page=per_page,
        total=total,
    )


@app.route("/session/<session_id>")
@requires_auth
def session_detail(session_id):
    session_id_safe = sanitize_input(session_id, max_length=256)

    if not validate_session_id(session_id_safe):
        return "Invalid session ID", 400

    # Fast path: look up export_path from index, render .md directly
    index = load_index()
    meta = next(
        (s for s in index.get("sessions", []) if s.get("id") == session_id_safe),
        None,
    )

    export_path = meta.get("export_path") if meta else None

    # Fallback: scan .md headers if not in index
    if not export_path:
        import re as _re
        for md_file in (OUTPUT_DIR / "projects").rglob("*.md"):
            try:
                with open(md_file, "r", encoding="utf-8", errors="replace") as f:
                    header = f.read(300)
                if session_id_safe in header:
                    export_path = str(md_file)
                    break
            except OSError:
                pass

    if not export_path or not Path(export_path).exists():
        return "Session not found - run 'ai-history reindex' to rebuild the index", 404

    # Read and render the .md file directly
    try:
        with open(export_path, "r", encoding="utf-8", errors="replace") as f:
            md_content = f.read()
    except OSError as e:
        return f"Error reading session file: {e}", 500

    # Build a lightweight session-like object from index metadata + md content
    class _Session:
        pass

    session = _Session()
    session.session_id = session_id_safe
    session.title = (meta or {}).get("title") or f"Session {session_id_safe[:8]}"
    session.tool = type("T", (), {"value": (meta or {}).get("tool", "unknown")})()
    session.project_path = (meta or {}).get("project", "")
    session.created_at = type("D", (), {
        "isoformat": lambda self: (meta or {}).get("created", ""),
        "strftime": lambda self, fmt: (meta or {}).get("created", "")[:10],
    })()
    session.message_count = (meta or {}).get("messages", 0)
    session.messages = []  # Not needed - we render .md directly

    # Parse TOC from .md headings (### User lines)
    import re as _re
    toc_items = []
    for m in _re.finditer(r"^### User.*?\n+> (.+?)(?:\n|$)", md_content, _re.MULTILINE):
        text = m.group(1).strip()
        if text and not text.startswith("<"):
            toc_items.append({
                "index": len(toc_items),
                "text": text[:80],
                "raw": text,
            })

    # Render .md as HTML
    session.md_content = format_content(md_content)

    return render(
        "session",
        title=session.title,
        active="sessions",
        session=session,
        toc_items=toc_items,
        md_only=True,
    )


@app.route("/api/search")
@requires_auth
def api_search():
    """API endpoint for live search."""
    query = sanitize_input(request.args.get("q", ""), max_length=500)

    if len(query) < 2:
        return jsonify([])

    if len(query) > 500:
        return jsonify({"error": "Query too long"}), 400

    engine = ai_history.SearchEngine(INDEX_PATH)
    results = engine.search(query)[:20]

    return jsonify(
        [
            {
                "id": r.session.get("id", ""),
                "title": r.session.get("title")
                or r.session.get("project")
                or r.session.get("id", "")[:20],
                "tool": r.session.get("tool", "unknown"),
                "date": r.session.get("created", "")[:10],
                "icon": TOOL_STYLES.get(r.session.get("tool", ""), {}).get(
                    "icon", "🤖"
                ),
                "bg": TOOL_STYLES.get(r.session.get("tool", ""), {}).get(
                    "bg", "#2d3748"
                ),
            }
            for r in results
        ]
    )


@app.route("/api/stats")
@requires_auth
def api_stats():
    """API endpoint for stats."""
    index = load_index()
    return jsonify(index.get("stats", {}))


@app.route("/export/<session_id>")
@requires_auth
def export_session(session_id):
    """Export a session as Markdown."""
    session_id_safe = sanitize_input(session_id, max_length=256)

    if not validate_session_id(session_id_safe):
        return "Invalid session ID", 400

    extractors = ai_history.get_all_extractors()

    for extractor in extractors:
        if not extractor.is_available():
            continue

        for session in extractor.extract_sessions():
            if (
                session.session_id == session_id_safe
                or session_id_safe in session.session_id
            ):
                exporter = ai_history.MarkdownExporter(OUTPUT_DIR)
                content = exporter._generate_markdown(session)

                return Response(
                    content,
                    mimetype="text/markdown",
                    headers={
                        "Content-Disposition": f"attachment; filename={session_id[:8]}.md"
                    },
                )

    return "Session not found", 404


@app.route("/settings")
@requires_auth
def settings():
    """Settings page with sync configuration."""
    try:
        from sync import RcloneBackend

        backend = RcloneBackend()
        sync_status = backend.status()
    except (ImportError, AttributeError, OSError):
        sync_status = {
            "backend": "rclone",
            "rclone_available": False,
            "remote_configured": False,
        }

    # Get detected tools info
    extractors = ai_history.get_all_extractors()
    detected_tools = []

    tool_paths = {
        "claude-code": "~/.claude/projects/",
        "cursor": "~/.config/Cursor/User/globalStorage/state.vscdb",
        "gemini-cli": "~/.gemini/",
        "warp": "~/.local/state/warp-terminal/warp.sqlite",
        "codex": "~/.codex/sessions/",
        "vscode-copilot": "~/.config/Code/User/workspaceStorage/",
        "copilot-cli": "~/.copilot/",
    }

    for extractor in extractors:
        tool_name = extractor.__class__.__name__.replace("Extractor", "").lower()
        # Map class names to tool names
        name_mapping = {
            "claudecode": "claude-code",
            "geminicli": "gemini-cli",
            "vscodecopilot": "vscode-copilot",
            "copilotcli": "copilot-cli",
        }
        tool_name = name_mapping.get(tool_name, tool_name)

        detected_tools.append(
            {
                "name": tool_name,
                "path": tool_paths.get(tool_name, "Unknown"),
                "available": extractor.is_available(),
            }
        )

    return render(
        "settings",
        title="Settings",
        active="settings",
        sync_status=sync_status,
        detected_tools=detected_tools,
    )


@app.route("/api/sync/push", methods=["POST"])
def api_sync_push():
    """Push to cloud storage."""
    try:
        from sync import RcloneBackend

        backend = RcloneBackend()
        if backend.push():
            return redirect(url_for("settings") + "?msg=push_success")
        else:
            return redirect(url_for("settings") + "?msg=push_failed")
    except Exception as e:
        return redirect(url_for("settings") + f"?msg=error&detail={str(e)}")


@app.route("/api/sync/pull", methods=["POST"])
def api_sync_pull():
    """Pull from cloud storage."""
    try:
        from sync import RcloneBackend

        backend = RcloneBackend()
        if backend.pull():
            clear_index_cache()
            return redirect(url_for("settings") + "?msg=pull_success")
        else:
            return redirect(url_for("settings") + "?msg=pull_failed")
    except Exception as e:
        return redirect(url_for("settings") + f"?msg=error&detail={str(e)}")


@app.route("/api/rebuild-index", methods=["POST"])
def api_rebuild_index():
    """Rebuild the search index."""
    try:
        # Run export to rebuild index
        import subprocess

        result = subprocess.run(
            [
                "python3",
                str(Path(__file__).parent / "ai-history.py"),
                "export",
                "--all",
            ],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent),
        )
        clear_index_cache()
        return redirect(url_for("settings") + "?msg=rebuild_success")
    except Exception as e:
        return redirect(url_for("settings") + f"?msg=error&detail={str(e)}")


if __name__ == "__main__":
    print("=" * 50)
    print("ai-history Web UI v2.0")
    print("=" * 50)
    print(f"Index: {INDEX_PATH}")
    print(f"Open: http://localhost:5000")
    print("=" * 50)
    print("\nKeyboard shortcuts:")
    print("  ⌘K / Ctrl+K  - Quick search")
    print("  G then D     - Go to Dashboard")
    print("  Escape       - Close search")
    print("=" * 50)
    app.run(debug=False, host="0.0.0.0", port=5000, use_reloader=False)
