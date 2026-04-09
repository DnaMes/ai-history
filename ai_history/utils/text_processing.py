import re
import html
import json


def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from text."""
    if not text:
        return ""
    return re.compile(r"\x1B(?:[@-Z\\-_]|[0-?]*[ -/]*[@-~])").sub("", text)


def format_thinking(text: str) -> str:
    """Format <thinking> blocks as collapsible details (SpecStory Style)."""
    return f"""
    <details class="action-block group">
        <summary>
            <svg class="action-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="m9 18 6-6-6-6"/></svg>
            <span class="thinking-label">Thinking</span>
            <span class="thinking-summary">{html.escape(text[:80]).strip()}{'...' if len(text) > 80 else ''}</span>
        </summary>
        <div class="action-content">
            <div class="thinking-content">{html.escape(text)}</div>
        </div>
    </details>
    """


def _normalize_tool_name(raw_name: str) -> str:
    name = (raw_name or "tool").strip().replace("_", " ")
    return re.sub(r"\s+", " ", name)


def _tool_icon(tool_name: str) -> str:
    lowered = tool_name.lower()
    if "bash" in lowered or "shell" in lowered or "terminal" in lowered:
        return "⚡"
    if "read" in lowered:
        return "📄"
    if "write" in lowered or "edit" in lowered:
        return "🛠"
    if "search" in lowered or "grep" in lowered or "glob" in lowered:
        return "🔎"
    if "web" in lowered or "fetch" in lowered or "http" in lowered:
        return "🌐"
    return "🔧"


def _guess_language(tool_name: str, text: str) -> str:
    lowered_tool = tool_name.lower()
    lowered_text = text.lower()
    stripped_text = (text or "").lstrip()
    if (
        stripped_text.startswith("*** Begin Patch")
        or "@@" in text
        or "diff --git" in lowered_text
    ):
        return "diff"
    if "bash" in lowered_tool or "shell" in lowered_tool:
        return "bash"
    if "python" in lowered_tool or "python" in lowered_text:
        return "python"
    if "json" in lowered_tool or lowered_text.strip().startswith("{"):
        return "json"
    if "sql" in lowered_text or "sqlite" in lowered_text:
        return "sql"
    return "plaintext"


def _safe_preview(value: str, limit: int = 140) -> str:
    preview = re.sub(r"\s+", " ", value or "").strip()
    if len(preview) <= limit:
        return preview
    return preview[: limit - 3] + "..."


def _format_shell_command_for_display(command_text: str) -> str:
    command = (command_text or "").strip()
    if not command or "\n" in command or len(command) < 80:
        return command

    wrapped = re.sub(r"\s*(&&|\|\||\|)\s*", r" \1\n", command)
    wrapped = re.sub(r";\s+", ";\n", wrapped)
    wrapped = re.sub(r"[ \t]{2,}", " ", wrapped)
    return wrapped.strip()


def _tool_importance(tool_name: str) -> str:
    lowered = (tool_name or "").lower()
    important_tokens = (
        "bash",
        "shell",
        "write",
        "edit",
        "apply_patch",
        "deploy",
        "commit",
        "delete",
        "migrate",
        "sql",
    )
    if any(token in lowered for token in important_tokens):
        return "major"
    return "minor"


def _render_kv_grid(tool_input) -> str:
    if not isinstance(tool_input, dict) or not tool_input:
        return ""
    items = []
    for key, value in list(tool_input.items())[:8]:
        if isinstance(value, (dict, list)):
            value_display = json.dumps(value, ensure_ascii=False)
        else:
            value_display = str(value)
        items.append(
            '<div class="action-kv-item">'
            f'<div class="action-kv-key">{html.escape(str(key))}</div>'
            f'<div class="action-kv-value">{html.escape(_safe_preview(value_display, 220))}</div>'
            "</div>"
        )
    if not items:
        return ""
    return '<div class="action-kv-grid">' + "".join(items) + "</div>"


def format_tool_result(text: str) -> str:
    text = (text or "").strip()
    if not text:
        text = "(empty output)"

    lowered = text.lower()
    lines = text.split("\n")
    line_count = len(lines)
    char_count = len(text)

    status = "neutral"
    if any(token in lowered for token in ("error", "exception", "traceback", "failed")):
        status = "error"
    elif any(
        token in lowered
        for token in ("ok", "success", "completed", "created", "updated")
    ):
        status = "ok"

    first_line = next((line.strip() for line in lines if line.strip()), "Output")
    summary = _safe_preview(first_line, 90)

    exit_code = None
    exit_match = re.search(r"(?:exit\s*code|code)\s*[:=]?\s*(\d{1,3})", lowered)
    if exit_match:
        try:
            exit_code = int(exit_match.group(1))
        except ValueError:
            exit_code = None

    warning_count = len(re.findall(r"\bwarning\b", lowered))
    error_count = len(re.findall(r"\berror\b|\bexception\b|\btraceback\b", lowered))

    additions = 0
    deletions = 0
    for line in lines:
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+"):
            additions += 1
        elif line.startswith("-"):
            deletions += 1

    status_label = {
        "ok": "Success",
        "error": "Error",
        "neutral": "Result",
    }[status]

    chips = [
        f'<span class="action-meta">{line_count} lines</span>',
        f'<span class="action-meta">{char_count} chars</span>',
    ]
    if exit_code is not None:
        chips.append(f'<span class="action-meta">exit {exit_code}</span>')
    if warning_count > 0:
        chips.append(f'<span class="action-meta">warnings {warning_count}</span>')
    if error_count > 0:
        chips.append(f'<span class="action-meta">errors {error_count}</span>')
    if additions > 0 or deletions > 0:
        chips.append(f'<span class="action-meta">diff +{additions}/-{deletions}</span>')

    importance = (
        "major"
        if status == "error" or (exit_code is not None and exit_code != 0)
        else "minor"
    )

    return f"""
    <details class="action-block tool-result importance-{importance} group">
        <summary class="tool-call-pill tool-result-pill status-{status}">
            <svg class="action-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="m9 18 6-6-6-6"/></svg>
            <span class="tool-chip status-{status}">{status_label}</span>
            <span class="action-title truncate">Tool result</span>
            <span class="action-meta-group">{''.join(chips)}</span>
            <span class="truncate opacity-75">{html.escape(summary)}</span>
        </summary>
        <div class="action-content">
            <pre class="action-output"><code class="language-plaintext">{html.escape(text)}</code></pre>
        </div>
    </details>
    """


def format_tool_display(tool_name: str, args: str) -> str:
    normalized_tool = _normalize_tool_name(tool_name)
    icon = _tool_icon(normalized_tool)
    importance = _tool_importance(normalized_tool)

    raw_args = (args or "").strip()
    arg_display = raw_args or "(no arguments)"
    preview = _safe_preview(arg_display, 88)

    parsed_input = None
    if raw_args.startswith("{") or raw_args.startswith("["):
        try:
            parsed_input = json.loads(raw_args)
        except json.JSONDecodeError:
            parsed_input = None

    if parsed_input is not None:
        arg_display = json.dumps(parsed_input, indent=2, ensure_ascii=False)

    command_text = ""
    if isinstance(parsed_input, dict):
        command_value = parsed_input.get("command") or parsed_input.get("cmd")
        if isinstance(command_value, str):
            command_text = command_value.strip()
    if not command_text and "bash" in normalized_tool.lower() and raw_args:
        command_text = raw_args

    language = _guess_language(normalized_tool, command_text or arg_display)
    display_command = command_text
    if language == "bash":
        display_command = _format_shell_command_for_display(command_text)
    kv_grid = _render_kv_grid(parsed_input)

    command_block = ""
    if display_command:
        command_block = (
            '<div class="action-section-title">Command</div>'
            f'<pre class="action-code"><code class="language-{language}">{html.escape(display_command)}</code></pre>'
        )

    raw_block = (
        '<details class="action-raw">'
        "<summary>Raw arguments</summary>"
        f'<pre class="action-output"><code class="language-{language}">{html.escape(arg_display)}</code></pre>'
        "</details>"
    )

    return f"""
    <details class="action-block tool-action importance-{importance} group">
        <summary class="tool-call-pill">
            <svg class="action-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="m9 18 6-6-6-6"/></svg>
            <span class="tool-call-icon">{icon}</span>
            <span class="action-title">Run {html.escape(normalized_tool)}</span>
            <span class="action-meta">{len(arg_display)} chars</span>
            <span class="truncate opacity-75">{html.escape(preview)}</span>
        </summary>
        <div class="action-content">
            {command_block}
            {kv_grid}
            {raw_block}
        </div>
    </details>
    """
