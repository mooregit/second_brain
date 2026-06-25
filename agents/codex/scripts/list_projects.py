#!/usr/bin/env python3
from __future__ import annotations

import argparse

from secondbrain_client import SecondBrainClient, print_json


def main() -> None:
    parser = argparse.ArgumentParser(description="List Second Brain projects for agent project selection.")
    parser.add_argument("--json", action="store_true", help="Print raw JSON.")
    args = parser.parse_args()

    client = SecondBrainClient.from_env()
    projects = client.get("/projects")
    if args.json:
        print_json(projects)
        return
    for project in projects:
        description = f" - {project['description']}" if project.get("description") else ""
        print(f"{project['name']} ({project['id']}){description}")


if __name__ == "__main__":
    main()
