#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from secondbrain_client import SecondBrainClient, die, find_project


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract compact Second Brain project context for a coding agent.")
    parser.add_argument("--project", help="Project name or id.")
    parser.add_argument("--repo", default=".", help="Repo path to include in the header.")
    parser.add_argument("--output", help="Write Markdown context to this file instead of stdout.")
    args = parser.parse_args()

    client = SecondBrainClient.from_env()
    project = find_project(client, args.project)
    if args.project and not project:
        die(f"Project not found: {args.project}")

    if project:
        brief = client.get(f"/projects/{project['id']}/brief")
        markdown = render_project_context(brief, Path(args.repo).resolve())
    else:
        markdown = render_general_context(client, Path(args.repo).resolve())

    if args.output:
        Path(args.output).write_text(markdown, encoding="utf-8")
    else:
        print(markdown)


def render_project_context(brief: dict, repo_path: Path) -> str:
    lines = [
        "# Second Brain Context",
        "",
        f"Repo: `{repo_path}`",
        f"Project: {brief['project']['name']}",
        "",
        "## Brief",
        "",
        brief["summary"],
        "",
        "## Next Actions",
        "",
    ]
    lines.extend(f"- {action}" for action in brief.get("next_actions", []))
    lines.extend(["", "## Project Flags", ""])
    for risk in brief.get("risks", []):
        lines.append(f"- {risk.replace('_', ' ')}")
    for failure in brief.get("github_failures", []):
        branch = f" on {failure['branch']}" if failure.get("branch") else ""
        lines.append(f"- GitHub Actions failing: {failure['name']} ({failure['repository']}{branch})")
    if not brief.get("risks") and not brief.get("github_failures"):
        lines.append("- None")
    lines.extend(["", "## Open Tasks", ""])
    lines.extend(render_records(brief.get("open_tasks", []), "title"))
    lines.extend(["", "## Open Questions", ""])
    lines.extend(render_records(brief.get("open_questions", []), "question"))
    lines.extend(["", "## Recent Decisions", ""])
    lines.extend(render_records(brief.get("recent_decisions", []), "title"))
    lines.extend(["", "## Active Ideas", ""])
    lines.extend(render_records(brief.get("active_ideas", []), "body"))
    lines.extend(["", "## Recent Sources", ""])
    for source in brief.get("recent_sources", []):
        lines.append(f"- {source['title']} (`raw_item_id={source['raw_item_id']}`)")
    return "\n".join(lines).strip() + "\n"


def render_general_context(client: SecondBrainClient, repo_path: Path) -> str:
    projects = client.get("/projects")
    lines = ["# Second Brain Context", "", f"Repo: `{repo_path}`", "", "## Projects", ""]
    lines.extend(f"- {project['name']} (`{project['id']}`)" for project in projects[:25])
    return "\n".join(lines).strip() + "\n"


def render_records(records: list[dict], label_key: str) -> list[str]:
    if not records:
        return ["- None"]
    lines = []
    for record in records:
        source = f" raw_item_id={record['source_raw_item_id']}" if record.get("source_raw_item_id") else ""
        lines.append(f"- {record.get(label_key, 'Untitled')} (`{record.get('id')}`{source})")
    return lines


if __name__ == "__main__":
    main()
