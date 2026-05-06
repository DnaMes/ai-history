import asyncio
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

from ..extractors.factory import get_all_extractors
from ..search.engine import SearchEngine
from ..exporters.index import IndexBuilder
from ..utils.datetime import parse_duration, make_naive
from ..utils.security import (
    validate_search_param,
    validate_session_id,
    validate_tool_name,
)
from ..utils.tooling import normalize_tool_name, to_session_switch_tool
from .api_payloads import (
    serialize_index_session_summary,
    serialize_live_session,
    serialize_project,
    serialize_thread_messages,
    serialize_thread_overview,
)
from .web_data import INDEX_PATH, load_index, load_sessions_for_tool
from .web_services import (
    build_projects_payload,
    build_thread_detail_payload,
    build_threads_overview,
)


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

    server.output_dir = INDEX_PATH.parent

    def _json_text(payload: dict) -> str:
        return json.dumps(payload, indent=2, ensure_ascii=False)

    def build_index_if_missing() -> None:
        if INDEX_PATH.exists():
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

    def _ensure_index() -> dict:
        if not INDEX_PATH.exists():
            build_index_if_missing()
        return load_index()

    def _normalize_limit(
        raw_value: object, default: int = 10, max_value: int = 100
    ) -> int:
        if raw_value is None:
            return default
        if not isinstance(raw_value, int) or raw_value < 1 or raw_value > max_value:
            raise ValueError(f"Invalid limit parameter (must be 1-{max_value}).")
        return raw_value

    def _load_live_session(session_id: str, tool_filter: Optional[str] = None):
        tools = []
        if tool_filter:
            tools.append(tool_filter)
        tools.extend(
            [
                tool_name
                for tool_name in sorted(
                    {
                        session.get("tool")
                        for session in _ensure_index().get("sessions", [])
                        if session.get("tool")
                    }
                )
                if tool_name not in tools
            ]
        )
        for tool_name in tools:
            try:
                sessions = load_sessions_for_tool(tool_name)
            except Exception:
                continue
            for session in sessions:
                if session.session_id == session_id:
                    return session
        return None

    def _session_meta_by_id(session_id: str) -> Optional[dict]:
        idx = _ensure_index()
        return next(
            (
                session
                for session in idx.get("sessions", [])
                if session.get("id") == session_id
            ),
            None,
        )

    async def search_history(args: dict) -> str:
        query = args.get("query", "")
        tool_filter = normalize_tool_name(args.get("tool") or "") or None
        project_filter = args.get("project") or None
        limit = _normalize_limit(args.get("limit"), default=10)

        if not query or not validate_search_param(query):
            return "Invalid search query parameter."
        if tool_filter and not validate_tool_name(tool_filter):
            return "Invalid tool parameter."
        if project_filter and not validate_search_param(project_filter):
            return "Invalid project parameter."

        _ensure_index()
        results = SearchEngine(INDEX_PATH).search(
            query,
            tool=tool_filter,
            project=project_filter,
        )[:limit]
        payload = {
            "query": query,
            "tool": tool_filter,
            "project": project_filter,
            "count": len(results),
            "results": [
                {
                    **serialize_index_session_summary(result["session"]),
                    "score": result.get("score"),
                }
                for result in results
            ],
        }
        return _json_text(payload)

    server.register_tool(
        "search_history",
        "Search across all AI chat sessions.",
        {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "tool": {"type": "string"},
                "project": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["query"],
        },
        search_history,
    )

    async def list_sessions(args: dict) -> str:
        tool_filter = normalize_tool_name(args.get("tool") or "") or None
        project_filter = args.get("project") or None
        thread_filter = args.get("thread_id") or None
        since = args.get("since")
        limit = _normalize_limit(args.get("limit"), default=20)

        if tool_filter and not validate_tool_name(tool_filter):
            return "Invalid tool parameter."
        if project_filter and not validate_search_param(project_filter):
            return "Invalid project parameter."
        if thread_filter and not validate_session_id(thread_filter):
            return "Invalid thread_id parameter."

        sessions = []
        cutoff = None
        if since:
            try:
                cutoff = datetime.now() - parse_duration(since)
            except ValueError:
                return "Invalid since parameter."

        for session in _ensure_index().get("sessions", []):
            if tool_filter and session.get("tool") != tool_filter:
                continue
            if project_filter and project_filter not in str(
                session.get("project") or ""
            ):
                continue
            if thread_filter and session.get("thread_id") != thread_filter:
                continue
            if cutoff:
                created = session.get("created")
                try:
                    created_dt = datetime.fromisoformat(
                        str(created).replace("Z", "+00:00")
                    )
                except ValueError:
                    created_dt = None
                if created_dt and make_naive(created_dt) < cutoff:
                    continue
            sessions.append(session)

        sessions.sort(
            key=lambda s: str(s.get("updated") or s.get("created") or ""), reverse=True
        )
        payload = {
            "count": min(len(sessions), limit),
            "sessions": [
                serialize_index_session_summary(session) for session in sessions[:limit]
            ],
        }
        return _json_text(payload)

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

    async def get_session(args: dict) -> str:
        session_id = args.get("session_id")
        include_messages = bool(args.get("include_messages", False))

        if not session_id or not validate_session_id(session_id):
            return "Invalid session_id parameter."

        session_meta = _session_meta_by_id(session_id)
        if not session_meta:
            return _json_text({"error": "Session not found", "session_id": session_id})

        live_session = _load_live_session(session_id, session_meta.get("tool"))
        if live_session:
            payload = serialize_live_session(
                live_session,
                session_meta=session_meta,
                include_messages=include_messages,
            )
        else:
            payload = serialize_index_session_summary(session_meta)
            payload["live"] = False
            if include_messages:
                payload["messages"] = []
        return _json_text(payload)

    server.register_tool(
        "get_session",
        "Get a single session by id.",
        {
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "include_messages": {"type": "boolean"},
            },
            "required": ["session_id"],
        },
        get_session,
    )

    async def get_session_messages(args: dict) -> str:
        session_id = args.get("session_id")
        limit = _normalize_limit(args.get("limit"), default=200, max_value=1000)

        if not session_id or not validate_session_id(session_id):
            return "Invalid session_id parameter."

        session_meta = _session_meta_by_id(session_id)
        if not session_meta:
            return _json_text({"error": "Session not found", "session_id": session_id})

        live_session = _load_live_session(session_id, session_meta.get("tool"))
        if not live_session:
            return _json_text(
                {
                    "session_id": session_id,
                    "message_count": 0,
                    "messages": [],
                    "live": False,
                }
            )

        messages = serialize_live_session(
            live_session,
            session_meta=session_meta,
            include_messages=True,
        )["messages"]
        return _json_text(
            {
                "session_id": session_id,
                "message_count": len(messages),
                "messages": messages[:limit],
                "live": True,
            }
        )

    server.register_tool(
        "get_session_messages",
        "Get live session messages by session id.",
        {
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["session_id"],
        },
        get_session_messages,
    )

    async def list_recent_sessions(args: dict) -> str:
        limit = _normalize_limit(args.get("limit"), default=10)
        sessions = sorted(
            _ensure_index().get("sessions", []),
            key=lambda session: str(
                session.get("updated") or session.get("created") or ""
            ),
            reverse=True,
        )
        return _json_text(
            {
                "count": min(len(sessions), limit),
                "sessions": [
                    serialize_index_session_summary(session)
                    for session in sessions[:limit]
                ],
            }
        )

    server.register_tool(
        "list_recent_sessions",
        "List recently updated sessions.",
        {
            "type": "object",
            "properties": {
                "limit": {"type": "integer"},
            },
        },
        list_recent_sessions,
    )

    async def list_projects(args: dict) -> str:
        limit = _normalize_limit(args.get("limit"), default=50)
        projects = build_projects_payload(
            _ensure_index().get("sessions", []), lambda value: value
        )
        return _json_text(
            {
                "count": min(len(projects), limit),
                "projects": [
                    serialize_project(project) for project in projects[:limit]
                ],
            }
        )

    server.register_tool(
        "list_projects",
        "List projects present in the history index.",
        {
            "type": "object",
            "properties": {
                "limit": {"type": "integer"},
            },
        },
        list_projects,
    )

    async def get_thread(args: dict) -> str:
        thread_id = args.get("thread_id")
        include_messages = bool(args.get("include_messages", False))

        if not thread_id or not validate_session_id(thread_id):
            return "Invalid thread_id parameter."

        idx = _ensure_index()
        overview = next(
            (
                thread
                for thread in build_threads_overview(idx.get("sessions", []))
                if thread.get("thread_id") == thread_id
            ),
            None,
        )
        if not overview:
            return _json_text({"error": "Thread not found", "thread_id": thread_id})

        payload: dict[str, object] = {"thread": serialize_thread_overview(overview)}
        if include_messages:
            detail = build_thread_detail_payload(
                thread_id,
                idx.get("sessions", []),
                load_sessions_for_tool,
                lambda value: value,
                lambda value: json.dumps(value, ensure_ascii=False),
                lambda tool_name: {"tool": tool_name, "name": tool_name},
            )
            payload["messages"] = serialize_thread_messages(detail["messages"])
            payload["thread_meta"] = detail["thread_meta"]
            payload["timeline"] = [
                serialize_index_session_summary(session)
                for session in detail["thread_timeline"]
            ]
        return _json_text(payload)

    server.register_tool(
        "get_thread",
        "Get a thread overview and optional messages.",
        {
            "type": "object",
            "properties": {
                "thread_id": {"type": "string"},
                "include_messages": {"type": "boolean"},
            },
            "required": ["thread_id"],
        },
        get_thread,
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
            return "Timeout: Command took longer than 30 seconds."
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
