# Read-Only MCP Tool Contract

This is the planned tool contract for the first MCP server wrapper.

## `secondbrain_list_projects`

List known Second Brain projects.

Input:

```json
{}
```

Output:

```json
{
  "projects": [
    {
      "id": "project-id",
      "name": "Project Name"
    }
  ]
}
```

## `secondbrain_get_project_context`

Fetch a compact project brief for coding-agent context.

Input:

```json
{
  "project": "Second Brain",
  "repo": "."
}
```

Output:

```json
{
  "markdown": "# Second Brain Context\n..."
}
```

## `secondbrain_search`

Search stored memories and source-linked records.

Input:

```json
{
  "query": "What did we decide about GitHub sync?"
}
```

Output:

```json
{
  "answer": "...",
  "sources": [
    {
      "title": "Source title",
      "raw_item_id": "raw-item-id"
    }
  ]
}
```

## `secondbrain_ask`

Ask a retrieval-grounded question against Second Brain.

Input:

```json
{
  "question": "What are the next steps for Second Brain?"
}
```

Output:

```json
{
  "answer": "...",
  "sources": []
}
```
