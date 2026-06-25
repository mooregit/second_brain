# Agent Safety Notes

Second Brain agent tools should stay proposal-first unless the user explicitly asks for a write.

## Read-Only Tools

These tools can be used freely when context helps the task:

- `list_projects.py`
- `extract_context.py`
- `search_secondbrain.py`
- `generate_prompt.py`

They fetch context, format prompts, or ask retrieval-backed questions. They do not create Second Brain records.

## Write Tools

These tools preview by default and require `--yes` before creating records:

- `save_session.py`
- `create_task.py`
- `create_question.py`
- `create_decision.py`
- `write_back.py`

Do not pass `--yes` unless the user approved the specific records to create.

## Config Rules

Configuration is layered in this order:

1. Packaged defaults in `agents/codex/secondbrain.yml`.
2. User defaults in `~/.config/secondbrain/agents/codex.yml`, or `SECONDBRAIN_AGENT_CONFIG`.
3. Repo-local `.secondbrain.yml`.
4. Environment variables such as `SECONDBRAIN_API_URL`.

Installed files are user-editable. Update tools should detect local edits and avoid silent replacement.

## Local Allowlist Guidance

Keep write access narrow:

- Enable read-only tools first.
- Require explicit user approval for tasks, questions, decisions, and session saves.
- Store raw item IDs and source titles when writing records.
- Keep generated state files local and out of commits.
