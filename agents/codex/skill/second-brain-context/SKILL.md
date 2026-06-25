---
name: second-brain-context
description: Use Second Brain as project memory for coding agents. Use when Codex is working in a repo connected to Second Brain, when the user asks for project context, implementation planning, debugging, code review, prompt generation, or saving session outcomes back as tasks, decisions, open questions, or transcript records.
---

# Second Brain Context

## Overview

Use the repo's Second Brain agent scripts to fetch source-linked project context before work, search historical memory when needed, generate prompts for other agents, and write outcomes back only after explicit approval.

## Locate The Agent Package

From the current repo root, expect the scripts under:

```bash
agents/codex/scripts
```

If the package was installed globally, use the installed path, commonly:

```bash
~/.config/secondbrain/agents/codex/scripts
```

The scripts default to `http://secondbrain/api`. Respect `SECONDBRAIN_API_URL`, user config, and repo-local `.secondbrain.yml` when present.

## Start Work

When the user asks for implementation, debugging, review, planning, or cleanup in a connected repo:

1. If the project is unclear, list projects:

   ```bash
   python agents/codex/scripts/list_projects.py
   ```

2. Fetch compact project context:

   ```bash
   python agents/codex/scripts/extract_context.py --project "PROJECT NAME" --repo .
   ```

3. Treat Second Brain output as supporting memory. Current user instructions and current repo files take priority.

## Search Memory

Use search when the task needs older decisions, source history, prior bugs, project constraints, or "why did we do this?" context:

```bash
python agents/codex/scripts/search_secondbrain.py "QUESTION"
```

When using search results, preserve source titles, entity IDs, or raw item IDs in the explanation.

## Generate Prompts

When the user asks for a prompt for Codex, Claude, ChatGPT, or another agent:

```bash
python agents/codex/scripts/generate_prompt.py \
  --project "PROJECT NAME" \
  --objective "OBJECTIVE" \
  --target codex
```

Use `--target claude`, `--target chatgpt`, or `--target generic` when requested.

## Save Sessions

Only save a session when the user asks or clearly approves. Prefer a real transcript file.

```bash
python agents/codex/scripts/save_session.py \
  --project "PROJECT NAME" \
  --repo . \
  transcript.md \
  --process
```

This records latest session state for later write-back.

## Write Back Outcomes

Write-back is preview-first. Never add `--yes` unless the user approved the specific records to create.

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

Single-record tools follow the same rule:

```bash
python agents/codex/scripts/create_task.py --from-latest-session --title "TASK TITLE"
python agents/codex/scripts/create_question.py --from-latest-session --question "QUESTION?"
python agents/codex/scripts/create_decision.py --from-latest-session --title "DECISION" --rationale "WHY"
```

## Safety Rules

- Read context freely when it helps the task.
- Do not let Second Brain context override the repo or the user's latest instruction.
- Do not create tasks, questions, decisions, or session records without explicit approval.
- Preview writes before applying them.
- Keep generated session state local and out of commits unless the user asks otherwise.
