import asyncio
import json
import sys
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional

from ..core.models import UnifiedSession
from ..extractors.factory import get_all_extractors
from ..search.engine import SearchEngine
from ..exporters.index import IndexBuilder
from ..utils.datetime import parse_duration, make_naive
from ..utils.paths import get_current_project
from ..utils.security import (
    validate_tool_name,
    validate_session_id,
    validate_search_param,
)
from ..utils.tooling import normalize_tool_name, to_session_switch_tool


class MCPServer:
    """Simple MCP Server implementation using stdio."""

    def __init__(self):
        self.tools = {}
        self.output_dir = Path.home() / ".ai-history"

    def register_tool(self, name: str, description: str, input_schema: dict, handler):
        """Register a tool with the server."""
        self.tools[name] = {
            "name": name,
            "description": description,
            "inputSchema": input_schema,
            "handler": handler,
        }

    async def handle_request(self, request: dict) -> Optional[dict]:
        """Handle an incoming JSON-RPC request."""
        method = request.get("method", "")
        params = request.get("params", {})
        request_id = request.get("id")

        if method == "initialize":
            return self._handle_initialize(request_id, params)
        elif method == "tools/list":
            return self._handle_tools_list(request_id)
        elif method == "tools/call":
            return await self._handle_tools_call(request_id, params)
        elif method == "notifications/initialized":
            return None  # No response for notifications
        else:
            return self._error_response(
                request_id, -32601, f"Method not found: {method}"
            )

    def _handle_initialize(self, request_id, params) -> dict:
        """Handle initialize request."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                },
                "serverInfo": {
                    "name": "ai-history",
                    "version": "2.0.0",
                },
            },
        }

    def _handle_tools_list(self, request_id) -> dict:
        """Handle tools/list request."""
        tools = []
        for tool in self.tools.values():
            tools.append(
                {
                    "name": tool["name"],
                    "description": tool["description"],
                    "inputSchema": tool["inputSchema"],
                }
            )
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"tools": tools},
        }

    async def _handle_tools_call(self, request_id, params) -> dict:
        """Handle tools/call request."""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if tool_name not in self.tools:
            return self._error_response(
                request_id, -32602, f"Unknown tool: {tool_name}"
            )

        try:
            handler = self.tools[tool_name]["handler"]
            result = await handler(arguments)
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{"type": "text", "text": result}],
                },
            }
        except Exception as e:
            return self._error_response(request_id, -32603, str(e))

    def _error_response(self, request_id, code: int, message: str) -> dict:
        """Create an error response."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": code, "message": message},
        }

    async def run(self):
        """Run the server, reading from stdin and writing to stdout."""

        def read_exactly(num_bytes: int) -> bytes:
            data = b""
            while len(data) < num_bytes:
                chunk = sys.stdin.buffer.read(num_bytes - len(data))
                if not chunk:
                    return b""
                data += chunk
            return data

        def write_response(message: dict, use_content_length: bool) -> None:
            if use_content_length:
                payload = json.dumps(message).encode("utf-8")
                header = f"Content-Length: {len(payload)}\r\n\r\n".encode("ascii")
                sys.stdout.buffer.write(header + payload)
                sys.stdout.buffer.flush()
            else:
                sys.stdout.write(json.dumps(message) + "\n")
                sys.stdout.flush()

        while True:
            use_content_length = False
            try:
                line = await asyncio.get_event_loop().run_in_executor(
                    None, sys.stdin.buffer.readline
                )
                if not line:
                    break

                if line.strip() == b"":
                    continue

                if line.lower().startswith(b"content-length:"):
                    use_content_length = True
                    headers = {}
                    header_line = line.decode("utf-8", "replace").strip()
                    key, _, value = header_line.partition(":")
                    headers[key.lower()] = value.strip()

                    while True:
                        next_line = await asyncio.get_event_loop().run_in_executor(
                            None, sys.stdin.buffer.readline
                        )
                        if not next_line:
                            return
                        if next_line in (b"\r\n", b"\n", b""):
                            break
                        header_text = next_line.decode("utf-8", "replace").strip()
                        if not header_text:
                            break
                        h_key, _, h_value = header_text.partition(":")
                        headers[h_key.lower()] = h_value.strip()

                    content_length = int(headers.get("content-length", "0"))
                    if content_length <= 0:
                        continue

                    body = await asyncio.get_event_loop().run_in_executor(
                        None, read_exactly, content_length
                    )
                    if not body:
                        break
                    request = json.loads(body.decode("utf-8"))
                else:
                    request = json.loads(line.decode("utf-8").strip())
                response = await self.handle_request(request)

                if response is not None:
                    write_response(response, use_content_length)

            except json.JSONDecodeError as e:
                error = self._error_response(None, -32700, f"Parse error: {e}")
                write_response(error, use_content_length)
            except Exception as e:
                error = self._error_response(None, -32603, f"Internal error: {e}")
                write_response(error, use_content_length)


def create_server() -> MCPServer:
    """Create and configure the MCP server."""
    server = MCPServer()

    def build_index_if_missing() -> None:
        index_path = server.output_dir / "index.json"
        if index_path.exists():
            return
        extractors = get_all_extractors()
        sessions = []
        for extractor in extractors:
            if not extractor.is_available():
                continue
            try:
                sessions.extend(list(extractor.extract_sessions()))
            except Exception:
                continue
        IndexBuilder(server.output_dir).build_index(sessions, {})

    # search_history tool
    async def search_history(args: dict) -> str:
        query = args.get("query", "")
        tool_filter = args.get("tool")
        limit = args.get("limit", 10)

        if not query or not validate_search_param(query):
            return "Invalid search query parameter."

        if tool_filter and not validate_tool_name(tool_filter):
            return "Invalid tool parameter."

        if not isinstance(limit, int) or limit < 1 or limit > 100:
            return "Invalid limit parameter (must be 1-100)."

        index_path = server.output_dir / "index.json"
        if not index_path.exists():
            build_index_if_missing()
        if not index_path.exists():
            return "No index found. Please run 'ai-history export --all' first to build the index."

        engine = SearchEngine(index_path)
        results = engine.search(query, tool=tool_filter)[:limit]

        if not results:
            return f"No results found for '{query}'."

        output = [f"Found {len(results)} results for '{query}':\n"]
        for r in results:
            session = r["session"]
            output.append(
                f"- [{session['tool']}] {session.get('title', session['id'][:20])}"
            )
            output.append(
                f"  Date: {session['created'][:10]} | Messages: {session['messages']}"
            )
            if session.get("project"):
                output.append(f"  Project: {session['project']}")
            output.append("")

        return "\n".join(output)

    server.register_tool(
        "search_history",
        "Search across all AI chat sessions.",
        {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "tool": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["query"],
        },
        search_history,
    )

    # list_sessions tool
    async def list_sessions(args: dict) -> str:
        tool_filter = args.get("tool")
        project_filter = args.get("project")
        thread_filter = args.get("thread_id")
        since = args.get("since")
        limit = args.get("limit", 20)

        if tool_filter and not validate_tool_name(tool_filter):
            return "Invalid tool parameter."

        if project_filter and not validate_search_param(project_filter):
            return "Invalid project parameter."

        if thread_filter and not validate_session_id(thread_filter):
            return "Invalid thread_id parameter."

        if not isinstance(limit, int) or limit < 1 or limit > 100:
            return "Invalid limit parameter (must be 1-100)."

        extractors = get_all_extractors()
        sessions = []

        for extractor in extractors:
            if tool_filter and extractor.tool.value != tool_filter:
                continue
            if not extractor.is_available():
                continue

            for session in extractor.extract_sessions():
                if since:
                    try:
                        duration = parse_duration(since)
                        cutoff = datetime.now() - duration
                        if make_naive(session.created_at) < cutoff:
                            continue
                    except ValueError:
                        pass

                if project_filter:
                    if (
                        not session.project_path
                        or project_filter not in session.project_path
                    ):
                        continue
                if thread_filter and session.thread_id:
                    if session.thread_id != thread_filter:
                        continue

                sessions.append(session)

        sessions.sort(key=lambda s: make_naive(s.last_updated), reverse=True)
        sessions = sessions[:limit]

        if not sessions:
            return "No sessions found matching the criteria."

        output = [f"Found {len(sessions)} sessions:\n"]
        for s in sessions:
            date_str = s.created_at.strftime("%Y-%m-%d")
            title = s.title or s.project_path or s.session_id[:20]
            if len(title) > 35:
                title = title[:32] + "..."
            output.append(
                f"{s.tool.value:<15} {date_str:<12} {s.message_count:>6}  {title}"
            )

        return "\n".join(output)

    server.register_tool(
        "list_sessions",
        "List AI chat sessions with optional filters.",
        {
            "type": "object",
            "properties": {
                "tool": {"type": "string"},
                "project": {"type": "string"},
                "thread_id": {"type": "string"},
                "since": {"type": "string"},
                "limit": {"type": "integer"},
            },
        },
        list_sessions,
    )

    # switch_to_tool tool
    async def switch_to_tool(args: dict) -> str:
        tool = args.get("tool", "gemini")
        max_messages = args.get("max_messages", 15)
        thread_id = args.get("thread_id")

        normalized_tool = normalize_tool_name(tool)
        if not normalized_tool or not validate_tool_name(normalized_tool):
            return "Invalid tool name. Must be one of: claude-code, cursor, gemini-cli, etc."

        if not isinstance(max_messages, int) or max_messages < 1 or max_messages > 1000:
            return "Invalid max_messages parameter (must be 1-1000)."

        if thread_id and not validate_session_id(thread_id):
            return "Invalid thread_id parameter."

        switch_tool = to_session_switch_tool(normalized_tool)
        if not switch_tool:
            return f"Tool '{normalized_tool}' is not supported by ai-session switch."

        cmd = ["ai-session", "switch", switch_tool, "--messages", str(max_messages)]
        if thread_id:
            cmd.extend(["--thread-id", thread_id])

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=False, timeout=30
            )
            if result.returncode == 0:
                return f"✓ Context prepared for {normalized_tool}.\n\n{result.stdout}"
            else:
                return f"Failed to switch to {normalized_tool}:\n{result.stderr}"
        except subprocess.TimeoutExpired:
            return f"Timeout: Command took longer than 30 seconds."
        except FileNotFoundError:
            return "ai-session command not found."

    server.register_tool(
        "switch_to_tool",
        "Switch to another AI tool with context.",
        {
            "type": "object",
            "properties": {
                "tool": {"type": "string"},
                "max_messages": {"type": "integer"},
                "thread_id": {"type": "string"},
            },
            "required": ["tool"],
        },
        switch_to_tool,
    )

    return server
