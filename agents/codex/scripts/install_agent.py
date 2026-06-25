#!/usr/bin/env python3
from __future__ import annotations

import argparse
import difflib
import filecmp
import shutil
import sys
from datetime import datetime
from pathlib import Path


AGENT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TARGET = Path.home() / ".config" / "secondbrain" / "agents" / "codex"
PACKAGE_FILES = [
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
    "skill/second-brain-context/SKILL.md",
    "skill/second-brain-context/agents/openai.yaml",
]
PACKAGE_DIRS = ["scripts"]
PACKAGE_GLOBS = ["mcp/*.py"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Install or update the Second Brain Codex agent package.")
    parser.add_argument("--target", default=str(DEFAULT_TARGET), help="Install target directory.")
    parser.add_argument("--yes", action="store_true", help="Apply changes. Without this, print a dry-run plan.")
    parser.add_argument(
        "--on-conflict",
        choices=["keep", "diff", "backup-and-replace", "install-as-new"],
        default="keep",
        help="How to handle changed target files.",
    )
    parser.add_argument("--reset", action="store_true", help="Replace target files from templates, backing up conflicts.")
    parser.add_argument("--diff", action="store_true", help="Show diffs between packaged templates and target files.")
    args = parser.parse_args()

    target = Path(args.target).expanduser().resolve()
    actions = plan_install(target, args.on_conflict, reset=args.reset, diff_only=args.diff)
    if args.diff:
        print_diff(actions)
        return

    print_plan(target, actions, dry_run=not args.yes)
    if not args.yes:
        print("\nRerun with --yes to apply.")
        return

    apply_actions(actions)


def plan_install(target: Path, conflict_mode: str, reset: bool = False, diff_only: bool = False) -> list[dict]:
    actions: list[dict] = []
    for relative in PACKAGE_FILES:
        source = AGENT_ROOT / relative
        destination = target / relative
        actions.append(plan_file(source, destination, conflict_mode, reset=reset, diff_only=diff_only))
    for relative_dir in PACKAGE_DIRS:
        for source in sorted((AGENT_ROOT / relative_dir).glob("*.py")):
            destination = target / relative_dir / source.name
            actions.append(plan_file(source, destination, conflict_mode, reset=reset, diff_only=diff_only))
    for pattern in PACKAGE_GLOBS:
        for source in sorted(AGENT_ROOT.glob(pattern)):
            destination = target / source.relative_to(AGENT_ROOT)
            actions.append(plan_file(source, destination, conflict_mode, reset=reset, diff_only=diff_only))
    return actions


def plan_file(source: Path, destination: Path, conflict_mode: str, reset: bool = False, diff_only: bool = False) -> dict:
    action = {"source": source, "destination": destination, "operation": "copy"}
    if not destination.exists():
        return action
    if filecmp.cmp(source, destination, shallow=False):
        action["operation"] = "unchanged"
    elif diff_only:
        action["operation"] = "diff"
    elif reset:
        action["operation"] = "backup-and-replace"
    elif conflict_mode == "install-as-new":
        action["operation"] = "install-as-new"
        action["destination"] = new_path(destination)
    else:
        action["operation"] = conflict_mode
    return action


def apply_actions(actions: list[dict]) -> None:
    for action in actions:
        operation = action["operation"]
        source = action["source"]
        destination = action["destination"]
        if operation in {"unchanged", "keep", "diff"}:
            continue
        if operation == "backup-and-replace" and destination.exists():
            backup = backup_path(destination)
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(destination, backup)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        if source.suffix == ".py":
            destination.chmod(destination.stat().st_mode | 0o111)


def print_plan(target: Path, actions: list[dict], dry_run: bool) -> None:
    mode = "Dry run" if dry_run else "Applying"
    print(f"{mode}: install Second Brain Codex agent to {target}")
    for action in actions:
        relative = action["source"].relative_to(AGENT_ROOT)
        print(f"- {action['operation']}: {relative} -> {action['destination']}")


def print_diff(actions: list[dict]) -> None:
    for action in actions:
        destination = action["destination"]
        if not destination.exists():
            continue
        source = action["source"]
        source_lines = source.read_text(encoding="utf-8").splitlines(keepends=True)
        dest_lines = destination.read_text(encoding="utf-8").splitlines(keepends=True)
        diff = difflib.unified_diff(
            dest_lines,
            source_lines,
            fromfile=str(destination),
            tofile=str(source),
        )
        sys.stdout.writelines(diff)


def backup_path(path: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return path.with_name(f"{path.name}.backup-{stamp}")


def new_path(path: Path) -> Path:
    counter = 1
    while True:
        candidate = path.with_name(f"{path.name}.new-{counter}")
        if not candidate.exists():
            return candidate
        counter += 1


if __name__ == "__main__":
    main()
