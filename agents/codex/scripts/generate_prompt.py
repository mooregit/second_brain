#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from secondbrain_client import SecondBrainClient, die, find_project
from extract_context import render_project_context


TARGET_INSTRUCTIONS = {
    "codex": "You are Codex working in this repository. Inspect the code before editing, keep changes scoped, run relevant checks, and report files changed plus verification.",
    "claude": "You are an engineering assistant. Use the provided project context, reason carefully, propose or implement a focused solution, and preserve source traceability.",
    "chatgpt": "Use the project context below to answer or plan clearly. Distinguish facts from assumptions and include concrete next steps.",
    "generic": "Use the project context below to complete the objective. Preserve decisions, constraints, and source references.",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a context-rich prompt for Codex, Claude, ChatGPT, or another agent.")
    parser.add_argument("--project", required=True, help="Second Brain project name or id.")
    parser.add_argument("--objective", required=True, help="The work objective for the generated prompt.")
    parser.add_argument("--repo", default=".", help="Repo path to include in context.")
    parser.add_argument("--target", choices=sorted(TARGET_INSTRUCTIONS), default="codex")
    parser.add_argument("--constraints", action="append", default=[], help="Constraint to include. Can be repeated.")
    parser.add_argument("--output", help="Write prompt to this file instead of stdout.")
    args = parser.parse_args()

    client = SecondBrainClient.from_env()
    project = find_project(client, args.project)
    if not project:
        die(f"Project not found: {args.project}")
    brief = client.get(f"/projects/{project['id']}/brief")
    context = render_project_context(brief, Path(args.repo).resolve())
    prompt = render_prompt(args.objective, args.target, args.constraints, context)

    if args.output:
        Path(args.output).write_text(prompt, encoding="utf-8")
    else:
        print(prompt)


def render_prompt(objective: str, target: str, constraints: list[str], context: str) -> str:
    lines = [
        "# Agent Prompt",
        "",
        "## Role",
        "",
        TARGET_INSTRUCTIONS[target],
        "",
        "## Objective",
        "",
        objective,
        "",
    ]
    if constraints:
        lines.extend(["## Constraints", ""])
        lines.extend(f"- {constraint}" for constraint in constraints)
        lines.append("")
    lines.extend(
        [
            "## Required Output",
            "",
            "- Explain the approach briefly before major changes.",
            "- Preserve source links, raw item IDs, and decision context where relevant.",
            "- List changed files and verification steps.",
            "- Capture any new tasks, decisions, or open questions that should be written back to Second Brain.",
            "",
            "## Second Brain Context",
            "",
            context.strip(),
        ]
    )
    return "\n".join(lines).strip() + "\n"


if __name__ == "__main__":
    main()
