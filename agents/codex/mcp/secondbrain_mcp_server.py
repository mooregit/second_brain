#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable


AGENT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = AGENT_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from extract_context import render_project_context  # noqa: E402
from secondbrain_client import SecondBrainClient, SecondBrainError, find_project, save_state  # noqa: E402


READ_ONLY_TOOLS = {"secondbrain_list_projects", "secondbrain_get_project_context", "secondbrain_search", "secondbrain_ask"}
WRITE_TOOLS = {
    "secondbrain_create_note",
    "secondbrain_create_task",
    "secondbrain_create_open_question",
    "secondbrain_record_decision",
    "secondbrain_save_session",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Second Brain MCP stdio server.")
    parser.add_argument("--mode", choices=["read-only", "write-enabled"], default=os.environ.get("SECONDBRAIN_MCP_MODE", "read-only"))
    args = parser.parse_args()
    server = MCPServer(mode=args.mode)
    server.run()


class MCPServer:
    def __init__(self, mode: str) -> None:
        self.mode = mode
        self.client = SecondBrainClient.from_env()

    @property
    def writes_allowed(self) -> bool:
        return self.mode == "write-enabled" and os.environ.get("SECONDBRAIN_MCP_ALLOW_WRITES", "false").lower() == "true"

    @property
    def require_write_confirmation(self) -> bool:
        return os.environ.get("SECONDBRAIN_MCP_REQUIRE_APPROVAL", "true").lower() != "false"

    def run(self) -> None:
        for line in sys.stdin:
            if not line.strip():
                continue
            try:
                request = json.loads(line)
                response = self.handle_request(request)
            except Exception as exc:
                response = error_response(None, -32603, str(exc))
            if response is not None:
                print(json.dumps(response), flush=True)

    def handle_request(self, request: dict[str, Any]) -> dict[str, Any] | None:
        method = request.get("method")
        request_id = request.get("id")
        if request_id is None:
            return None
        handlers: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
            "initialize": self.initialize,
            "tools/list": self.list_tools,
            "tools/call": self.call_tool,
            "ping": lambda _params: {},
        }
        handler = handlers.get(str(method))
        if not handler:
            return error_response(request_id, -32601, f"Unknown method: {method}")
        try:
            return {"jsonrpc": "2.0", "id": request_id, "result": handler(request.get("params") or {})}
        except SecondBrainError as exc:
            return error_response(request_id, -32000, str(exc))
        except ValueError as exc:
            return error_response(request_id, -32602, str(exc))

    def initialize(self, _params: dict[str, Any]) -> dict[str, Any]:
        return {
            "protocolVersion": "2024-11-05",
            "serverInfo": {"name": "secondbrain", "version": "0.1.0"},
            "capabilities": {"tools": {}},
        }

    def list_tools(self, _params: dict[str, Any]) -> dict[str, Any]:
        tools = [
            tool_schema("secondbrain_list_projects", "List Second Brain projects.", {}),
            tool_schema(
                "secondbrain_get_project_context",
                "Fetch compact source-linked project context as Markdown.",
                {
                    "project": {"type": "string", "description": "Project name or id."},
                    "repo": {"type": "string", "description": "Repository path for context header.", "default": "."},
                },
                required=["project"],
            ),
            tool_schema(
                "secondbrain_search",
                "Search Second Brain memory and return an answer with sources.",
                {"query": {"type": "string", "description": "Search query or question."}},
                required=["query"],
            ),
            tool_schema(
                "secondbrain_ask",
                "Ask a retrieval-grounded question against Second Brain.",
                {"question": {"type": "string", "description": "Question to answer from Second Brain."}},
                required=["question"],
            ),
        ]
        if self.writes_allowed:
            tools.extend(write_tool_schemas())
        return {"tools": tools}

    def call_tool(self, params: dict[str, Any]) -> dict[str, Any]:
        name = str(params.get("name") or "")
        arguments = params.get("arguments") or {}
        if name in WRITE_TOOLS and not self.writes_allowed:
            return text_result(f"{name} is unavailable because this server is running in read-only mode.", is_error=True)
        tools: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
            "secondbrain_list_projects": self.tool_list_projects,
            "secondbrain_get_project_context": self.tool_get_project_context,
            "secondbrain_search": self.tool_search,
            "secondbrain_ask": self.tool_ask,
            "secondbrain_create_note": self.tool_create_note,
            "secondbrain_create_task": self.tool_create_task,
            "secondbrain_create_open_question": self.tool_create_open_question,
            "secondbrain_record_decision": self.tool_record_decision,
            "secondbrain_save_session": self.tool_save_session,
        }
        tool = tools.get(name)
        if not tool:
            raise ValueError(f"Unknown tool: {name}")
        return tool(arguments)

    def tool_list_projects(self, _args: dict[str, Any]) -> dict[str, Any]:
        projects = self.client.get("/projects")
        return json_result({"projects": projects}, render_projects(projects))

    def tool_get_project_context(self, args: dict[str, Any]) -> dict[str, Any]:
        project_name = require_str(args, "project")
        repo = Path(str(args.get("repo") or ".")).resolve()
        project = find_project(self.client, project_name)
        if not project:
            raise ValueError(f"Project not found: {project_name}")
        brief = self.client.get(f"/projects/{project['id']}/brief")
        markdown = render_project_context(brief, repo)
        return json_result({"markdown": markdown, "project": project}, markdown)

    def tool_search(self, args: dict[str, Any]) -> dict[str, Any]:
        query = require_str(args, "query")
        response = self.client.post("/ask", {"question": query})
        return json_result(response, render_ask_response(response, "Second Brain Search"))

    def tool_ask(self, args: dict[str, Any]) -> dict[str, Any]:
        question = require_str(args, "question")
        response = self.client.post("/ask", {"question": question})
        return json_result(response, render_ask_response(response, "Second Brain Ask"))

    def tool_create_note(self, args: dict[str, Any]) -> dict[str, Any]:
        payload = {"title": require_str(args, "title"), "body_text": require_str(args, "body")}
        return self.preview_or_apply(args, "/items/manual", payload)

    def tool_create_task(self, args: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "memory_id": require_str(args, "memory_id"),
            "title": require_str(args, "title"),
            "description": optional_str(args, "description"),
            "priority": optional_str(args, "priority"),
            "status": str(args.get("status") or "open"),
            "project_id": self.resolve_project_id(args),
        }
        return self.preview_or_apply(args, "/tasks", payload)

    def tool_create_open_question(self, args: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "memory_id": require_str(args, "memory_id"),
            "question": require_str(args, "question"),
            "status": str(args.get("status") or "open"),
            "project_id": self.resolve_project_id(args),
        }
        return self.preview_or_apply(args, "/open-questions", payload)

    def tool_record_decision(self, args: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "memory_id": require_str(args, "memory_id"),
            "title": require_str(args, "title"),
            "rationale": optional_str(args, "rationale"),
            "confidence": float(args.get("confidence", 0.8)),
            "project_id": self.resolve_project_id(args),
        }
        return self.preview_or_apply(args, "/decisions", payload)

    def tool_save_session(self, args: dict[str, Any]) -> dict[str, Any]:
        transcript = require_str(args, "transcript")
        repo = Path(str(args.get("repo") or ".")).resolve()
        project = find_project(self.client, optional_str(args, "project"))
        title = optional_str(args, "title") or f"Agent session: {project['name'] if project else repo.name}"
        body = render_session_body(transcript, repo, project)
        preview_payload = {"title": title, "body_text": body}
        if not self.confirmed(args):
            return json_result({"preview": preview_payload}, "Preview only. Pass confirm=true to save this session.")
        item = self.client.post("/items/manual", preview_payload)
        result: dict[str, Any] = {"raw_item": item}
        if bool(args.get("process")):
            result["processing_run"] = self.client.post(f"/items/{item['id']}/process")
        session_state = {
            "raw_item_id": item["id"],
            "memory_id": find_first_memory_id(self.client, item["id"]),
            "project_id": project["id"] if project else None,
            "project_name": project["name"] if project else None,
            "repo": str(repo),
            "title": title,
        }
        save_state({"latest_session": session_state})
        result["latest_session"] = session_state
        return json_result(result, f"Saved session raw_item_id={item['id']}")

    def preview_or_apply(self, args: dict[str, Any], path: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.confirmed(args):
            return json_result({"preview": payload}, "Preview only. Pass confirm=true to create this record.")
        created = self.client.post(path, payload)
        return json_result(created, f"Created record at {path}: {created.get('id', 'unknown id')}")

    def confirmed(self, args: dict[str, Any]) -> bool:
        if not self.require_write_confirmation:
            return True
        return bool(args.get("confirm"))

    def resolve_project_id(self, args: dict[str, Any]) -> str | None:
        project_id = optional_str(args, "project_id")
        if project_id:
            return project_id
        project_name = optional_str(args, "project")
        if not project_name:
            return None
        project = find_project(self.client, project_name)
        if not project:
            raise ValueError(f"Project not found: {project_name}")
        return str(project["id"])


def write_tool_schemas() -> list[dict[str, Any]]:
    return [
        tool_schema(
            "secondbrain_create_note",
            "Preview or create a raw note. Requires confirm=true to write.",
            {
                "title": {"type": "string"},
                "body": {"type": "string"},
                "confirm": {"type": "boolean", "default": False},
            },
            required=["title", "body"],
        ),
        tool_schema(
            "secondbrain_create_task",
            "Preview or create a source-linked task. Requires confirm=true to write.",
            write_schema({"title": {"type": "string"}, "description": {"type": "string"}, "priority": {"type": "string"}, "status": {"type": "string"}}),
            required=["memory_id", "title"],
        ),
        tool_schema(
            "secondbrain_create_open_question",
            "Preview or create a source-linked open question. Requires confirm=true to write.",
            write_schema({"question": {"type": "string"}, "status": {"type": "string"}}),
            required=["memory_id", "question"],
        ),
        tool_schema(
            "secondbrain_record_decision",
            "Preview or create a source-linked decision. Requires confirm=true to write.",
            write_schema({"title": {"type": "string"}, "rationale": {"type": "string"}, "confidence": {"type": "number"}}),
            required=["memory_id", "title"],
        ),
        tool_schema(
            "secondbrain_save_session",
            "Preview or save an agent session transcript. Requires confirm=true to write.",
            {
                "title": {"type": "string"},
                "transcript": {"type": "string"},
                "project": {"type": "string"},
                "repo": {"type": "string", "default": "."},
                "process": {"type": "boolean", "default": False},
                "confirm": {"type": "boolean", "default": False},
            },
            required=["transcript"],
        ),
    ]


def write_schema(extra: dict[str, Any]) -> dict[str, Any]:
    base = {
        "memory_id": {"type": "string"},
        "project": {"type": "string"},
        "project_id": {"type": "string"},
        "confirm": {"type": "boolean", "default": False},
    }
    base.update(extra)
    return base


def tool_schema(name: str, description: str, properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "inputSchema": {"type": "object", "properties": properties, "required": required or []},
    }


def require_str(args: dict[str, Any], key: str) -> str:
    value = args.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} is required")
    return value.strip()


def optional_str(args: dict[str, Any], key: str) -> str | None:
    value = args.get(key)
    if value is None:
        return None
    return str(value).strip() or None


def render_projects(projects: list[dict[str, Any]]) -> str:
    if not projects:
        return "No projects found."
    return "\n".join(f"- {project.get('name', 'Untitled')} (`{project.get('id')}`)" for project in projects)


def render_ask_response(response: dict[str, Any], title: str) -> str:
    lines = [f"# {title}", "", response.get("answer") or "", "", "## Sources", ""]
    sources = response.get("sources") or []
    if not sources:
        lines.append("- None")
    for source in sources:
        source_title = source.get("title") or source.get("owner_type") or "Source"
        raw_item_id = source.get("raw_item_id") or ""
        lines.append(f"- {source_title} (`raw_item_id={raw_item_id}`)")
    return "\n".join(lines).strip()


def render_session_body(transcript: str, repo_path: Path, project: dict[str, Any] | None) -> str:
    branch = current_branch(repo_path)
    lines = ["Assistant session transcript", "", f"Repo: {repo_path}", f"Branch: {branch or 'unknown'}"]
    if project:
        lines.append(f"Second Brain project: {project['name']} ({project['id']})")
    lines.extend(["", "Transcript:", "", transcript.strip()])
    return "\n".join(lines).strip()


def current_branch(repo_path: Path) -> str | None:
    try:
        result = subprocess.run(["git", "branch", "--show-current"], cwd=repo_path, check=False, capture_output=True, text=True)
    except OSError:
        return None
    return result.stdout.strip() or None


def find_first_memory_id(client: SecondBrainClient, raw_item_id: str) -> str | None:
    try:
        item_detail = client.get(f"/items/{raw_item_id}")
    except Exception:
        return None
    memories = item_detail.get("memories") or []
    return memories[0].get("id") if memories else None


def json_result(data: Any, text: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": text}], "structuredContent": data}


def text_result(text: str, is_error: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {"content": [{"type": "text", "text": text}]}
    if is_error:
        result["isError"] = True
    return result


def error_response(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


if __name__ == "__main__":
    main()
