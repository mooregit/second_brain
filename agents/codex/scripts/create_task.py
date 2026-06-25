#!/usr/bin/env python3
from __future__ import annotations

import argparse

from secondbrain_client import SecondBrainClient, die, find_project, latest_session_memory_id, print_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a Second Brain task from an agent session.")
    parser.add_argument("--memory-id", help="Memory id that should own the task.")
    parser.add_argument("--from-latest-session", action="store_true", help="Use the latest memory saved by save_session.py.")
    parser.add_argument("--title", required=True)
    parser.add_argument("--description")
    parser.add_argument("--priority", choices=["low", "medium", "high"])
    parser.add_argument("--project", help="Project name or id.")
    parser.add_argument("--yes", action="store_true", help="Actually create the task. Without this, only preview.")
    args = parser.parse_args()

    client = SecondBrainClient.from_env()
    memory_id = args.memory_id or (latest_session_memory_id() if args.from_latest_session else None)
    if not memory_id:
        die("Pass --memory-id or --from-latest-session.")
    project = find_project(client, args.project)
    if args.project and not project:
        die(f"Project not found: {args.project}")
    payload = {
        "memory_id": memory_id,
        "title": args.title,
        "description": args.description,
        "priority": args.priority,
        "project_id": project["id"] if project else None,
    }
    if not args.yes:
        print_json({"preview": payload, "message": "Add --yes to create this task."})
        return
    print_json(client.post("/tasks", payload))


if __name__ == "__main__":
    main()
