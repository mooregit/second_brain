# Codex Agent Instructions For Second Brain

Use these scripts when working in a repo that should draw context from Second Brain or write session outcomes back to it.

## Default Setup

The scripts call `http://secondbrain/api` by default.

Override when needed:

```bash
export SECONDBRAIN_API_URL=http://localhost:8000
```

Config is layered from packaged defaults, user config at `~/.config/secondbrain/agents/codex.yml`, repo-local `.secondbrain.yml`, and environment variables.

## Start Of Work

When the user asks for implementation, debugging, planning, or review work tied to a known project:

1. List projects if the project name is unclear:

   ```bash
   python agents/codex/scripts/list_projects.py
   ```

2. Fetch project context:

   ```bash
   python agents/codex/scripts/extract_context.py --project "PROJECT NAME"
   ```

3. Use the returned context as background, not as unquestioned truth. Current repo files and direct user instructions still take priority.

## Prompt Generation

When the user wants a prompt for Codex, Claude, ChatGPT, or another coding agent:

```bash
python agents/codex/scripts/generate_prompt.py \
  --project "PROJECT NAME" \
  --objective "OBJECTIVE" \
  --target codex
```

Use `--target claude`, `--target chatgpt`, or `--target generic` when requested.

## Search

When specific historical context is needed:

```bash
python agents/codex/scripts/search_secondbrain.py "QUESTION"
```

Cite source titles or raw item IDs from the output when using the result.

## Save Session

Only save a session when the user asks or clearly approves.

```bash
python agents/codex/scripts/save_session.py \
  --project "PROJECT NAME" \
  --repo . \
  transcript.md \
  --process
```

This records latest session state in `.secondbrain-agent-state.json`.

## Write Back

Write-back tools are preview-first. Never add `--yes` unless the user has approved the specific records to create.

Preview:

```bash
python agents/codex/scripts/write_back.py \
  --from-latest-session \
  --task "TASK TITLE" \
  --question "OPEN QUESTION?" \
  --decision "DECISION TITLE" \
  --rationale "DECISION RATIONALE"
```

Apply only after explicit approval:

```bash
python agents/codex/scripts/write_back.py ... --yes
```

Single-record tools follow the same safety rule:

```bash
python agents/codex/scripts/create_task.py --from-latest-session --title "TASK TITLE"
python agents/codex/scripts/create_question.py --from-latest-session --question "QUESTION?"
python agents/codex/scripts/create_decision.py --from-latest-session --title "DECISION" --rationale "WHY"
```

Add `--yes` only after approval.

## Safety Rules

- Read context freely when it helps the task.
- Treat Second Brain context as supporting memory, not source of truth over the repo or user.
- Preserve raw item IDs and source titles when referencing stored context.
- Do not write tasks, questions, decisions, or sessions without explicit approval.
- Preview write-back before applying it.
- Keep generated session state local and out of committed changes unless explicitly requested.
