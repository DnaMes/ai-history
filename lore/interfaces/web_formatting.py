"""Message formatting and HTML sanitization for the web interface.

This module handles content formatting, tool call display, and HTML sanitization
for the web interface.
"""

import html
import json
import re

import markdown
import nh3

from lore.utils.text_processing import strip_ansi

from .web_data import threadsafe_lru_cache

# HTML sanitization constants (nh3 requires sets, not lists)
SANITIZE_TAGS = {
    "p",
    "br",
    "strong",
    "em",
    "u",
    "code",
    "pre",
    "a",
    "ul",
    "ol",
    "li",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "blockquote",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
    "hr",
    "div",
    "span",
    # Used by tool-call / thinking collapsible blocks generated internally
    "details",
    "summary",
}

SANITIZE_ATTRS = {
    "a": {"href", "title"},
    "code": {"class"},
    "pre": {"class"},
    "span": {"class"},
    "div": {"class"},
    "details": {"class"},
    "summary": {"class"},
}

SANITIZE_URL_SCHEMES = {"http", "https", "mailto"}


def sanitize_rendered_html(rendered_html: str) -> str:
    """Sanitize HTML content for safe display."""
    return nh3.clean(
        rendered_html or "",
        tags=SANITIZE_TAGS,
        attributes=SANITIZE_ATTRS,
        url_schemes=SANITIZE_URL_SCHEMES,
        strip_comments=True,
        link_rel=None,
    )


@threadsafe_lru_cache(maxsize=4096)
def _format_message_content_cached(raw_content: str) -> str:
    """Format message content with caching for performance."""
    from lore.utils.text_processing import (
        format_thinking,
        format_tool_display,
        format_tool_result,
    )

    content = strip_ansi(raw_content)
    placeholders = {}
    placeholder_idx = 0

    def next_key(prefix: str) -> str:
        nonlocal placeholder_idx
        placeholder_idx += 1
        return f"{prefix}{placeholder_idx}"

    def repl_think(m):
        k = next_key("THINK")
        placeholders[k] = format_thinking(m.group(1))
        return k

    content = re.sub(
        r"<(?:thinking|think)>(.*?)</(?:thinking|think)>",
        repl_think,
        content,
        flags=re.DOTALL,
    )

    def repl_cmd_msg(m):
        k = next_key("CMDMESSAGE")
        placeholders[k] = f'<code class="cmd-tag">{html.escape(m.group(2))}</code>'
        return k

    content = re.sub(
        r"<(command-message)>(.*?)</\1>",
        repl_cmd_msg,
        content,
        flags=re.DOTALL,
    )

    def repl_cmd_name(m):
        k = next_key("CMDNAME")
        placeholders[k] = f'<code class="cmd-name">{html.escape(m.group(2))}</code>'
        return k

    content = re.sub(
        r"<(command-name)>(.*?)</\1>",
        repl_cmd_name,
        content,
        flags=re.DOTALL,
    )

    def repl_cmd_args(m):
        k = next_key("CMDARGS")
        placeholders[k] = f'<code class="cmd-args">{html.escape(m.group(2))}</code>'
        return k

    content = re.sub(
        r"<(command-args)>(.*?)</\1>",
        repl_cmd_args,
        content,
        flags=re.DOTALL,
    )

    def repl_res(m):
        k = next_key("TOOLRES")
        placeholders[k] = format_tool_result(m.group(1))
        return k

    content = re.sub(
        r"\[Tool Result\]\s*\n(.*?)(?=\n\[Tool:|\n\[Tool Result\]|\Z)",
        repl_res,
        content,
        flags=re.DOTALL,
    )

    def repl_call(m):
        k = next_key("TOOLCALL")
        placeholders[k] = format_tool_display(m.group(1), m.group(2))
        return k

    content = re.sub(
        r"\[Tool:\s*([^\]]+)\]\s*(.*?)(?=\n\[Tool:|\n\[Tool Result\]|\nTOOLRES\d+|\Z)",
        repl_call,
        content,
        flags=re.DOTALL,
    )

    if markdown:
        content = markdown.markdown(content, extensions=["fenced_code", "tables", "nl2br"])
        content = nh3.clean(
            content,
            tags=SANITIZE_TAGS | {"code"},
            attributes=SANITIZE_ATTRS,
            url_schemes=SANITIZE_URL_SCHEMES,
            strip_comments=True,
            link_rel=None,
        )
    else:
        content = html.escape(content).replace("\n", "<br>")

    for k, v in placeholders.items():
        content = content.replace(f"<p>{k}</p>", v).replace(k, v)

    # Final sanitization pass over the fully-composed string; catches any
    # injection that slipped through placeholder re-injection above.
    return sanitize_rendered_html(content)


def format_message_content(content):
    """Format message content for display."""
    if not content:
        return ""
    return _format_message_content_cached(content)


def format_tool_calls(tool_calls):
    """Format tool calls for display."""
    from lore.utils.text_processing import format_tool_display, format_tool_result

    if not tool_calls:
        return ""
    from lore.core.models import normalize_tool_call

    blocks = []
    for raw_tc in tool_calls:
        tc = normalize_tool_call(raw_tc)
        tool_name = str(tc["tool"])
        # Identical consecutive calls are folded upstream (#83); show the count.
        burst = raw_tc.get("_burst_count", 1) if isinstance(raw_tc, dict) else 1
        if burst > 1:
            tool_name = f"{tool_name} ×{burst}"
        tool_input = tc["input"]
        if isinstance(tool_input, (dict, list)):
            tool_args = json.dumps(tool_input, indent=2, ensure_ascii=False)
        else:
            tool_args = str(tool_input)
        blocks.append(format_tool_display(tool_name, tool_args))

        tool_output = tc["output"]
        if isinstance(tool_output, str) and tool_output.strip():
            blocks.append(format_tool_result(tool_output))
    return "\n".join(blocks)


__all__ = [
    "SANITIZE_TAGS",
    "SANITIZE_ATTRS",
    "SANITIZE_URL_SCHEMES",
    "sanitize_rendered_html",
    "_format_message_content_cached",
    "format_message_content",
    "format_tool_calls",
]
