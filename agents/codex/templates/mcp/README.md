# Second Brain MCP Templates

These templates define the intended MCP connection shape for Second Brain agent clients.

The read-only template is the default mode and should be used first. It exposes context and retrieval tools only.

The write-enabled template is for a future server mode where write tools still require explicit approval before creating records.

## Planned Tools

Read-only mode:

- `secondbrain_search`
- `secondbrain_ask`
- `secondbrain_get_project_context`
- `secondbrain_list_projects`

Write-enabled mode:

- all read-only tools
- `secondbrain_create_note`
- `secondbrain_create_task`
- `secondbrain_create_open_question`
- `secondbrain_record_decision`
- `secondbrain_save_session`

## Usage

Copy one of the example files into the MCP client configuration location for Codex, Claude Desktop, or another MCP-compatible client.

Set `SECONDBRAIN_API_URL` to the backend URL reachable from that client. For local development this is usually:

```bash
http://localhost:8000
```

The referenced `mcp/secondbrain_mcp_server.py` command is included in the agent package. It is a small stdio MCP wrapper around the existing Second Brain HTTP API.
