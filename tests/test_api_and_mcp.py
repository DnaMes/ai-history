import asyncio
import json
from datetime import datetime

from ai_history.core.models import Role, Tool, UnifiedMessage, UnifiedSession
from ai_history.interfaces import mcp, web


def _build_live_session(session_id: str = "session-1", thread_id: str = "thread-1"):
    return UnifiedSession(
        tool=Tool.CLAUDE_CODE,
        session_id=session_id,
        created_at=datetime(2026, 4, 1, 10, 0, 0),
        last_updated=datetime(2026, 4, 1, 10, 5, 0),
        project_path="/repo/demo",
        thread_id=thread_id,
        title="Claude debugging session",
        messages=[
            UnifiedMessage(
                role=Role.USER,
                content="Find the sqlite issue",
                timestamp=datetime(2026, 4, 1, 10, 0, 0),
            ),
            UnifiedMessage(
                role=Role.ASSISTANT,
                content="I found the locking bug",
                timestamp=datetime(2026, 4, 1, 10, 1, 0),
            ),
        ],
    )


def _index_payload(session_id: str = "session-1", thread_id: str = "thread-1"):
    return {
        "sessions": [
            {
                "id": session_id,
                "tool": "claude-code",
                "title": "Claude debugging session",
                "created": "2026-04-01T10:00:00",
                "updated": "2026-04-01T10:05:00",
                "project": "/repo/demo",
                "thread_id": thread_id,
                "messages": 2,
                "prompts": 1,
                "export_path": None,
            }
        ],
        "stats": {
            "total_sessions": 1,
            "total_messages": 2,
            "by_tool": {"claude-code": 1},
            "by_project": {"/repo/demo": 1},
        },
    }


def test_api_v1_sessions_and_projects_return_json_shapes(monkeypatch):
    monkeypatch.setattr(web, "load_index", lambda: _index_payload())

    with web.app.test_client() as client:
        sessions_response = client.get("/api/v1/sessions")
        projects_response = client.get("/api/v1/projects")

    assert sessions_response.status_code == 200
    sessions_payload = sessions_response.get_json()
    assert sessions_payload["count"] == 1
    assert sessions_payload["sessions"][0]["id"] == "session-1"
    assert sessions_payload["sessions"][0]["tool"] == "claude-code"

    assert projects_response.status_code == 200
    projects_payload = projects_response.get_json()
    assert projects_payload["count"] == 1
    assert projects_payload["projects"][0]["path"] == "/repo/demo"


def test_api_v1_session_detail_and_messages_use_live_session(monkeypatch):
    live_session = _build_live_session()
    monkeypatch.setattr(web, "load_index", lambda: _index_payload())
    monkeypatch.setattr(web, "load_sessions_for_tool", lambda _tool=None: [live_session])

    with web.app.test_client() as client:
        detail_response = client.get("/api/v1/sessions/session-1")
        messages_response = client.get("/api/v1/sessions/session-1/messages")

    assert detail_response.status_code == 200
    detail_payload = detail_response.get_json()
    assert detail_payload["live"] is True
    assert detail_payload["assistant_message_count"] == 1

    assert messages_response.status_code == 200
    messages_payload = messages_response.get_json()
    assert messages_payload["message_count"] == 2
    assert messages_payload["messages"][0]["role"] == "user"
    assert messages_payload["messages"][1]["content"] == "I found the locking bug"


def test_api_v1_thread_detail_returns_serialized_messages(monkeypatch):
    live_session = _build_live_session()
    monkeypatch.setattr(web, "load_index", lambda: _index_payload())
    monkeypatch.setattr(web, "load_sessions_for_tool", lambda _tool=None: [live_session])

    with web.app.test_client() as client:
        response = client.get("/api/v1/threads/thread-1")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["thread"]["id"] == "thread-1"
    assert payload["thread"]["message_count"] == 2
    assert payload["timeline"][0]["id"] == "session-1"
    assert payload["messages"][0]["role"] == "user"


def test_mcp_server_returns_structured_json_for_new_tools(monkeypatch):
    live_session = _build_live_session()
    monkeypatch.setattr(mcp, "load_index", lambda: _index_payload())
    monkeypatch.setattr(mcp, "load_sessions_for_tool", lambda _tool=None: [live_session])

    server = mcp.create_server()

    tools_response = asyncio.run(
        server.handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    )
    tool_names = {tool["name"] for tool in tools_response["result"]["tools"]}
    assert "get_session" in tool_names
    assert "get_thread" in tool_names
    assert "list_projects" in tool_names

    session_response = asyncio.run(
        server.handle_request(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "get_session",
                    "arguments": {"session_id": "session-1"},
                },
            }
        )
    )
    session_payload = json.loads(session_response["result"]["content"][0]["text"])
    assert session_payload["id"] == "session-1"
    assert session_payload["live"] is True

    thread_response = asyncio.run(
        server.handle_request(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "get_thread",
                    "arguments": {"thread_id": "thread-1", "include_messages": True},
                },
            }
        )
    )
    thread_payload = json.loads(thread_response["result"]["content"][0]["text"])
    assert thread_payload["thread"]["id"] == "thread-1"
    assert len(thread_payload["messages"]) == 2
