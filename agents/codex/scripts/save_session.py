#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from secondbrain_client import SecondBrainClient, default_project_name, find_project, print_json, save_state


def main() -> None:
    parser = argparse.ArgumentParser(description="Save a Codex/agent session transcript into Second Brain.")
    parser.add_argument("transcript", nargs="?", help="Transcript file. Reads stdin when omitted.")
    parser.add_argument("--project", help="Related Second Brain project name or id. Defaults to secondbrain.yml default_project.")
    parser.add_argument("--repo", default=".", help="Repo path to include in metadata text.")
    parser.add_argument("--title", help="Raw item title.")
    parser.add_argument("--process", action="store_true", help="Queue extraction after saving.")
    args = parser.parse_args()

    transcript = read_transcript(args.transcript)
    repo_path = Path(args.repo).resolve()
    client = SecondBrainClient.from_env()
    project_name = args.project or default_project_name()
    project = find_project(client, project_name)
    body = render_session_body(transcript, repo_path, project)
    title = args.title or f"Codex session: {project['name'] if project else repo_path.name}"

    item = client.post("/items/manual", {"title": title, "body_text": body})
    result = {"raw_item": item}
    if args.process:
        result["processing_run"] = client.post(f"/items/{item['id']}/process")
    memory_id = find_first_memory_id(client, item["id"])
    session_state = {
        "raw_item_id": item["id"],
        "memory_id": memory_id,
        "project_id": project["id"] if project else None,
        "project_name": project["name"] if project else None,
        "repo": str(repo_path),
        "title": title,
    }
    save_state({"latest_session": session_state})
    result["latest_session"] = session_state
    print_json(result)


def read_transcript(path: str | None) -> str:
    if not path:
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def render_session_body(transcript: str, repo_path: Path, project: dict | None) -> str:
    branch = current_branch(repo_path)
    lines = [
        "Assistant session transcript",
        "",
        f"Repo: {repo_path}",
        f"Branch: {branch or 'unknown'}",
    ]
    if project:
        lines.append(f"Second Brain project: {project['name']} ({project['id']})")
    lines.extend(["", "Transcript:", "", transcript.strip()])
    return "\n".join(lines).strip()


def current_branch(repo_path: Path) -> str | None:
    try:
        result = subprocess.run(["git", "branch", "--show-current"], cwd=repo_path, check=False, capture_output=True, text=True)
    except OSError:
        return None
    branch = result.stdout.strip()
    return branch or None


def find_first_memory_id(client: SecondBrainClient, raw_item_id: str) -> str | None:
    try:
        item_detail = client.get(f"/items/{raw_item_id}")
    except Exception:
        return None
    memories = item_detail.get("memories") or []
    if not memories:
        return None
    return memories[0].get("id")


if __name__ == "__main__":
    main()
