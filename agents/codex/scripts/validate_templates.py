#!/usr/bin/env python3
from __future__ import annotations

import py_compile
import sys
from pathlib import Path


AGENT_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = [
    "AGENT.md",
    "README.md",
    "SAFETY.md",
    "secondbrain.yml",
    "config.example.yml",
    "templates/repo.secondbrain.yml",
    "templates/mcp/README.md",
    "templates/mcp/read-only.example.json",
    "templates/mcp/write-enabled.example.json",
    "templates/mcp/tools.read-only.md",
    "templates/mcp/tools.write-enabled.md",
    "mcp/secondbrain_mcp_server.py",
    "skill/second-brain-context/SKILL.md",
    "skill/second-brain-context/agents/openai.yaml",
    "scripts/secondbrain_client.py",
    "scripts/install_agent.py",
]
REQUIRED_TEXT = {
    "AGENT.md": ["extract_context.py", "write_back.py", "approval"],
    "SAFETY.md": ["Read-Only Tools", "Write Tools", "--yes"],
    "README.md": ["AGENT.md", "SAFETY.md", "install_agent.py", "MCP"],
    "skill/second-brain-context/SKILL.md": ["extract_context.py", "search_secondbrain.py", "write_back.py", "explicit approval"],
    "skill/second-brain-context/agents/openai.yaml": ["$second-brain-context"],
    "templates/mcp/README.md": ["read-only", "write-enabled", "secondbrain_mcp_server.py"],
    "templates/mcp/read-only.example.json": ["SECONDBRAIN_MCP_ALLOW_WRITES", "false"],
    "templates/mcp/write-enabled.example.json": ["SECONDBRAIN_MCP_REQUIRE_APPROVAL", "true"],
    "templates/mcp/tools.read-only.md": ["secondbrain_search", "secondbrain_get_project_context"],
    "templates/mcp/tools.write-enabled.md": ["approval-gated", "secondbrain_create_task"],
    "mcp/secondbrain_mcp_server.py": ["tools/list", "tools/call", "confirm=true"],
}


def main() -> None:
    errors: list[str] = []
    for relative in REQUIRED_FILES:
        path = AGENT_ROOT / relative
        if not path.exists():
            errors.append(f"missing {relative}")
    for relative, snippets in REQUIRED_TEXT.items():
        path = AGENT_ROOT / relative
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for snippet in snippets:
            if snippet not in text:
                errors.append(f"{relative} missing required text: {snippet}")
    for script in sorted((AGENT_ROOT / "scripts").glob("*.py")):
        try:
            py_compile.compile(str(script), doraise=True)
        except py_compile.PyCompileError as exc:
            errors.append(f"{script.relative_to(AGENT_ROOT)} failed to compile: {exc.msg}")
    for script in sorted((AGENT_ROOT / "mcp").glob("*.py")):
        try:
            py_compile.compile(str(script), doraise=True)
        except py_compile.PyCompileError as exc:
            errors.append(f"{script.relative_to(AGENT_ROOT)} failed to compile: {exc.msg}")
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        raise SystemExit(1)
    print("Agent templates validated.")


if __name__ == "__main__":
    main()
