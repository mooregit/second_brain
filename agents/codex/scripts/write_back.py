#!/usr/bin/env python3
from __future__ import annotations

import argparse
from typing import Any

from secondbrain_client import SecondBrainClient, die, find_project, latest_session_memory_id, print_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Preview or write multiple agent findings back to Second Brain.")
    parser.add_argument("--memory-id", help="Memory id that should own created records.")
    parser.add_argument("--from-latest-session", action="store_true", help="Use the latest memory saved by save_session.py.")
    parser.add_argument("--project", help="Project name or id. Defaults to latest session project when available.")
    parser.add_argument("--task", action="append", default=[], help="Task title. Can be repeated.")
    parser.add_argument("--question", action="append", default=[], help="Open question text. Can be repeated.")
    parser.add_argument("--decision", action="append", default=[], help="Decision title. Can be repeated.")
    parser.add_argument("--rationale", action="append", default=[], help="Decision rationale by order. Can be repeated.")
    parser.add_argument("--yes", action="store_true", help="Actually create records. Without this, only preview.")
    args = parser.parse_args()

    client = SecondBrainClient.from_env()
    memory_id = resolve_memory_id(args.memory_id, args.from_latest_session)
    if not memory_id:
        die("No memory id available. Pass --memory-id or run save_session.py --process and then use --from-latest-session.")

    project_name = args.project or latest_session_project_name()
    project = find_project(client, project_name)
    if project_name and not project:
        die(f"Project not found: {project_name}")

    operations = build_operations(memory_id, project["id"] if project else None, args.task, args.question, args.decision, args.rationale)
    if not operations:
        die("No write-back operations requested. Pass --task, --question, or --decision.")

    if not args.yes:
        print_json({"preview": operations, "message": "Add --yes to create these records."})
        return

    created = []
    for operation in operations:
        created.append(client.post(operation["path"], operation["payload"]))
    print_json({"created": created})


def resolve_memory_id(memory_id: str | None, from_latest_session: bool) -> str | None:
    if memory_id:
        return memory_id
    if from_latest_session:
        return latest_session_memory_id()
    return None


def latest_session_project_name() -> str | None:
    from secondbrain_client import latest_session

    session = latest_session()
    if not session:
        return None
    project_name = session.get("project_name")
    return str(project_name) if project_name else None


def build_operations(
    memory_id: str,
    project_id: str | None,
    tasks: list[str],
    questions: list[str],
    decisions: list[str],
    rationales: list[str],
) -> list[dict[str, Any]]:
    operations: list[dict[str, Any]] = []
    for title in tasks:
        operations.append(
            {
                "type": "task",
                "path": "/tasks",
                "payload": {"memory_id": memory_id, "title": title, "project_id": project_id, "status": "open"},
            }
        )
    for question in questions:
        operations.append(
            {
                "type": "open_question",
                "path": "/open-questions",
                "payload": {"memory_id": memory_id, "question": question, "project_id": project_id, "status": "open"},
            }
        )
    for index, title in enumerate(decisions):
        rationale = rationales[index] if index < len(rationales) else None
        operations.append(
            {
                "type": "decision",
                "path": "/decisions",
                "payload": {"memory_id": memory_id, "title": title, "rationale": rationale, "confidence": 0.8, "project_id": project_id},
            }
        )
    return operations


if __name__ == "__main__":
    main()
