#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


DEFAULT_API_URL = "http://secondbrain/api"
AGENT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = AGENT_ROOT / "secondbrain.yml"
DEFAULT_STATE_FILE = ".secondbrain-agent-state.json"
USER_CONFIG_PATH = Path(
    os.environ.get(
        "SECONDBRAIN_AGENT_CONFIG",
        str(Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "secondbrain" / "agents" / "codex.yml"),
    )
)


class SecondBrainError(RuntimeError):
    pass


@dataclass
class SecondBrainClient:
    api_url: str

    @classmethod
    def from_env(cls) -> "SecondBrainClient":
        config = load_config()
        return cls(os.environ.get("SECONDBRAIN_API_URL", config.get("api_url", DEFAULT_API_URL)).rstrip("/"))

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        query = f"?{urlencode(params)}" if params else ""
        return self._request("GET", f"{path}{query}")

    def post(self, path: str, payload: dict[str, Any] | None = None) -> Any:
        return self._request("POST", path, payload)

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = Request(
            f"{self.api_url}{path}",
            data=body,
            method=method,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        try:
            with urlopen(request, timeout=60) as response:
                text = response.read().decode("utf-8")
                return json.loads(text) if text else {}
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise SecondBrainError(f"{method} {path} failed with {exc.code}: {detail}") from exc
        except URLError as exc:
            raise SecondBrainError(f"{method} {path} failed: {exc}") from exc


def find_project(client: SecondBrainClient, name_or_id: str | None) -> dict[str, Any] | None:
    if not name_or_id:
        return None
    projects = client.get("/projects")
    normalized = normalize(name_or_id)
    for project in projects:
        if project.get("id") == name_or_id or normalize(project.get("name", "")) == normalized:
            return project
    return None


def default_project_name() -> str | None:
    value = load_config().get("default_project")
    return str(value) if value else None


def load_config() -> dict[str, Any]:
    config: dict[str, Any] = {}
    for path in [CONFIG_PATH, USER_CONFIG_PATH, find_repo_config()]:
        if path and path.exists():
            config.update(read_simple_yaml(path))
    return config


def find_repo_config(start: Path | None = None) -> Path | None:
    current = (start or Path.cwd()).resolve()
    for directory in [current, *current.parents]:
        candidate = directory / ".secondbrain.yml"
        if candidate.exists():
            return candidate
    return None


def read_simple_yaml(path: Path) -> dict[str, Any]:
    config: dict[str, Any] = {}
    current_list_key: str | None = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("-"):
            if current_list_key:
                config.setdefault(current_list_key, []).append(line[1:].strip())
            continue
        if ":" not in line:
            current_list_key = None
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not value:
            config[key] = []
            current_list_key = key
        elif value.lower() in {"true", "false"}:
            config[key] = value.lower() == "true"
            current_list_key = None
        else:
            config[key] = value
            current_list_key = None
    return config


def state_path() -> Path:
    configured = str(load_config().get("state_file", DEFAULT_STATE_FILE))
    path = Path(configured)
    return path if path.is_absolute() else AGENT_ROOT / path


def load_state() -> dict[str, Any]:
    path = state_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_state(update: dict[str, Any]) -> dict[str, Any]:
    state = load_state()
    state.update(update)
    path = state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    return state


def latest_session() -> dict[str, Any] | None:
    state = load_state()
    session = state.get("latest_session")
    return session if isinstance(session, dict) else None


def latest_session_memory_id() -> str | None:
    session = latest_session()
    if not session:
        return None
    memory_id = session.get("memory_id")
    return str(memory_id) if memory_id else None


def normalize(value: str) -> str:
    return " ".join(value.lower().strip().split())


def print_json(data: Any) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


def die(message: str, code: int = 1) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(code)
