# API Reference

`ai-history` exposes two integration surfaces for agents and tools:

1. MCP over stdio via `ai-history-mcp`
2. HTTP JSON endpoints via `ai-history-web`

Use MCP when the client already supports tool calling. Use HTTP when you are wiring a custom tool, service, plugin, or skill.

## Quick Start

Install or refresh entry points:

```bash
pip install -e .
```

Start the web API locally:

```bash
ai-history-web
```

Start the MCP server manually:

```bash
ai-history-mcp
```

## Claude Code

Add this to `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "ai-history": {
      "command": "ai-history-mcp",
      "args": []
    }
  }
}
```

If `ai-history-mcp` is not on `PATH`, use the full executable path.

Example prompts in Claude Code:

- `Search my history for sqlite locking fixes`
- `Find recent claude-code sessions in /repo/demo`
- `Show me the messages from session abc123`
- `Load thread thread-1 and summarize the prior work`

## OpenCode

Add this to `opencode.json`:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "ai-history": {
      "type": "local",
      "command": ["ai-history-mcp"]
    }
  }
}
```

If needed, replace `ai-history-mcp` with an absolute path.

## MCP Tools

All MCP tools return JSON text payloads so agents can parse the result deterministically.

### `search_history`

Search indexed sessions.

Input:

```json
{
  "query": "sqlite lock",
  "tool": "claude-code",
  "project": "/repo/demo",
  "limit": 10
}
```

Output shape:

```json
{
  "query": "sqlite lock",
  "tool": "claude-code",
  "project": "/repo/demo",
  "count": 1,
  "results": [
    {
      "id": "session-1",
      "tool": "claude-code",
      "title": "Claude debugging session",
      "created": "2026-04-01T10:00:00",
      "updated": "2026-04-01T10:05:00",
      "project": "/repo/demo",
      "thread_id": "thread-1",
      "message_count": 2,
      "prompt_count": 1,
      "export_path": null,
      "score": 0.42
    }
  ]
}
```

### `list_sessions`

List indexed sessions.

Input fields:

- `tool`: optional
- `project`: optional substring match
- `thread_id`: optional
- `since`: optional duration like `7d`
- `limit`: optional, default `20`

### `get_session`

Fetch one session.

Input:

```json
{
  "session_id": "session-1",
  "include_messages": true
}
```

Returns live session data when available. Otherwise returns indexed summary data with `"live": false`.

### `get_session_messages`

Fetch only messages for one session.

Input:

```json
{
  "session_id": "session-1",
  "limit": 200
}
```

### `list_recent_sessions`

List recently updated sessions.

Input:

```json
{
  "limit": 10
}
```

### `list_projects`

List projects present in the index.

Input:

```json
{
  "limit": 50
}
```

### `get_thread`

Fetch a thread overview and optional merged messages.

Input:

```json
{
  "thread_id": "thread-1",
  "include_messages": true
}
```

### `switch_to_tool`

Prepare a handoff to another CLI tool through `ai-session switch`.

Input:

```json
{
  "tool": "gemini-cli",
  "max_messages": 15,
  "thread_id": "thread-1"
}
```

## HTTP API

Base URL:

```text
http://127.0.0.1:5000
```

All endpoints below are read-only.

### `GET /api/v1/search`

Query params:

- `q`: required for useful results, minimum 2 chars
- `tool`: optional
- `project`: optional
- `limit`: optional, default `20`, max `200`

Example:

```bash
curl 'http://127.0.0.1:5000/api/v1/search?q=sqlite&tool=claude-code'
```

### `GET /api/v1/sessions`

Query params:

- `tool`: optional
- `project`: optional substring match
- `thread_id`: optional
- `q`: optional search term
- `limit`: optional, default `50`, max `500`

Example:

```bash
curl 'http://127.0.0.1:5000/api/v1/sessions?project=%2Frepo%2Fdemo&limit=25'
```

### `GET /api/v1/sessions/<session_id>`

Query params:

- `live=1`: allow broader live fallback lookup across tools

Example:

```bash
curl 'http://127.0.0.1:5000/api/v1/sessions/session-1'
```

### `GET /api/v1/sessions/<session_id>/messages`

Query params:

- `limit`: optional, default `500`, max `5000`

Example:

```bash
curl 'http://127.0.0.1:5000/api/v1/sessions/session-1/messages?limit=100'
```

### `GET /api/v1/projects`

Query params:

- `tool`: optional
- `limit`: optional, default `100`, max `500`

### `GET /api/v1/threads`

Query params:

- `limit`: optional, default `100`, max `500`

### `GET /api/v1/threads/<thread_id>`

Returns:

- `thread`: aggregate metadata
- `timeline`: indexed sessions in the thread
- `messages`: merged live messages across sessions
- `toc_items`: prompt previews
- `groups`: per-tool groupings
- `continue_command`: suggested `ai-session` continuation command

## Common Response Fields

Session summary fields:

- `id`
- `tool`
- `title`
- `display_title`
- `created`
- `updated`
- `project`
- `thread_id`
- `message_count`
- `prompt_count`
- `export_path`

Live session detail adds:

- `assistant_message_count`
- `total_tokens`
- `summary`
- `git_branch`
- `source_path`
- `cli_version`
- `live`

Message fields:

- `index`
- `message_id`
- `role`
- `timestamp`
- `content`
- `model`
- `tokens`
- `tool_calls`
- `reasoning`

## Integration Guidance For Agents

Recommended retrieval flow:

1. Use `search_history` or `GET /api/v1/search` to find candidate sessions.
2. Use `get_session` or `GET /api/v1/sessions/<id>` to inspect metadata.
3. Use `get_session_messages` or `GET /api/v1/sessions/<id>/messages` only when the session is relevant.
4. Use `get_thread` for cross-session continuity.

This keeps retrieval cheap and avoids loading full transcripts unless needed.

## Notes

- The API is local-first and intended for localhost workflows.
- Search is backed by the generated history index.
- Some detail endpoints return richer data when live session loading succeeds.
- Query and identifier parameters are validated strictly; invalid values return `400`.
