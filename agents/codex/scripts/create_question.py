#!/usr/bin/env python3
from __future__ import annotations

import argparse

from secondbrain_client import SecondBrainClient, die, find_project, latest_session_memory_id, print_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a Second Brain open question from an agent session.")
    parser.add_argument("--memory-id", help="Memory id that should own the open question.")
    parser.add_argument("--from-latest-session", action="store_true", help="Use the latest memory saved by save_session.py.")
    parser.add_argument("--question", required=True)
    parser.add_argument("--project", help="Project name or id.")
    parser.add_argument("--yes", action="store_true", help="Actually create the open question. Without this, only preview.")
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
        "question": args.question,
        "status": "open",
        "project_id": project["id"] if project else None,
    }
    if not args.yes:
        print_json({"preview": payload, "message": "Add --yes to create this open question."})
        return
    print_json(client.post("/open-questions", payload))


if __name__ == "__main__":
    main()
