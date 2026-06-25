# Second Brain Codex Agent

Small local scripts for letting Codex or another coding agent read from and write to Second Brain.

For agent behavior rules, see [AGENT.md](AGENT.md).
For write safety rules, see [SAFETY.md](SAFETY.md).

The scripts use the existing HTTP API and default to `http://secondbrain/api`. Override with:

```bash
export SECONDBRAIN_API_URL=http://localhost:8000
```

Config is layered from packaged defaults, `~/.config/secondbrain/agents/codex.yml`, repo-local `.secondbrain.yml`, then environment variables.

## Install or update

Dry run:

```bash
python agents/codex/scripts/install_agent.py --target ~/.config/secondbrain/agents/codex
```

Apply:

```bash
python agents/codex/scripts/install_agent.py --target ~/.config/secondbrain/agents/codex --yes
```

For changed local files, choose `--on-conflict keep`, `diff`, `backup-and-replace`, or `install-as-new`.

Validate packaged files:

```bash
python agents/codex/scripts/validate_templates.py
```

The Codex skill template lives at `agents/codex/skill/second-brain-context/SKILL.md`.

## MCP templates

Example MCP client configs live in `agents/codex/templates/mcp/`:

- `read-only.example.json` for context/search/Ask tools.
- `write-enabled.example.json` for write tools that still require approval.
- `tools.read-only.md` and `tools.write-enabled.md` define the planned tool contracts.

The bundled stdio server wrapper is `agents/codex/mcp/secondbrain_mcp_server.py`.

Smoke-test tool discovery:

```bash
printf '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}\n' \
  | python agents/codex/mcp/secondbrain_mcp_server.py --mode read-only
```

## Read-only context

```bash
python agents/codex/scripts/list_projects.py
python agents/codex/scripts/extract_context.py --project "Second Brain"
python agents/codex/scripts/search_secondbrain.py "Graphify GitHub Actions failures"
python agents/codex/scripts/generate_prompt.py --project "Second Brain" --objective "Add action item support" --target codex
```

## Save a session transcript

```bash
python agents/codex/scripts/save_session.py --project "Second Brain" --repo . transcript.md --process
```

This stores the latest session metadata in `agents/codex/.secondbrain-agent-state.json`.

## Write-back commands

Write commands preview by default. Add `--yes` to create records.

```bash
python agents/codex/scripts/create_task.py --memory-id MEMORY_ID --title "Add action item model" --project "Second Brain" --yes
python agents/codex/scripts/create_question.py --memory-id MEMORY_ID --question "Should completed action items remain in project briefs?" --project "Second Brain" --yes
python agents/codex/scripts/create_decision.py --memory-id MEMORY_ID --title "Keep completed tasks searchable" --rationale "Completion is operational state, not knowledge deletion." --yes
```

After saving a session with processing enabled, you can use the latest session instead of copying a memory id:

```bash
python agents/codex/scripts/write_back.py \
  --from-latest-session \
  --task "Add action item model" \
  --question "Should completed action items remain in project briefs?" \
  --decision "Completed records should stay searchable" \
  --rationale "Completion is operational state, not knowledge deletion."
```

Add `--yes` to create the previewed records.

## Safety

- Read scripts are safe by default.
- Write scripts require explicit `--yes`.
- Generated output is plain Markdown/JSON so it can be pasted into Codex, Claude, or another agent.
