# Write-Enabled MCP Tool Contract

Write-enabled mode should remain approval-gated. The server should preview the exact records to create and require explicit approval before applying writes.

## `secondbrain_create_note`

Create a raw note or session source record.

Input:

```json
{
  "title": "Implementation session",
  "body": "Transcript or note body",
  "project": "Second Brain",
  "source_type": "agent_session"
}
```

## `secondbrain_create_task`

Create a source-linked task.

Input:

```json
{
  "memory_id": "memory-id",
  "title": "Task title",
  "project": "Second Brain",
  "status": "open"
}
```

## `secondbrain_create_open_question`

Create a source-linked open question.

Input:

```json
{
  "memory_id": "memory-id",
  "question": "What should we decide?",
  "project": "Second Brain"
}
```

## `secondbrain_record_decision`

Create a source-linked decision.

Input:

```json
{
  "memory_id": "memory-id",
  "title": "Decision title",
  "rationale": "Why this was decided",
  "project": "Second Brain"
}
```

## `secondbrain_save_session`

Save an agent session transcript as a source record.

Input:

```json
{
  "title": "Codex session",
  "transcript": "Full transcript text",
  "project": "Second Brain",
  "repo": ".",
  "process": true
}
```
