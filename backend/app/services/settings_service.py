import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import AppSetting


class SettingsService:
    INBOX_FOLDER_KEY = "inbox_folder"
    GMAIL_ENABLED_KEY = "gmail_enabled"
    GMAIL_LABEL_KEY = "gmail_label"
    GMAIL_QUERY_KEY = "gmail_query"
    GMAIL_AUTO_PROCESS_KEY = "gmail_auto_process"
    GMAIL_LAST_SYNC_KEY = "gmail_last_sync_result"
    GITLAB_ENABLED_KEY = "gitlab_enabled"
    GITLAB_BASE_URL_KEY = "gitlab_base_url"
    GITLAB_TOKEN_KEY = "gitlab_token"
    GITLAB_PROJECTS_KEY = "gitlab_projects"
    GITLAB_AUTO_PROCESS_KEY = "gitlab_auto_process"
    GITLAB_LAST_SYNC_KEY = "gitlab_last_sync_result"
    GITHUB_ENABLED_KEY = "github_enabled"
    GITHUB_TOKEN_KEY = "github_token"
    GITHUB_REPOSITORIES_KEY = "github_repositories"
    GITHUB_AUTO_PROCESS_KEY = "github_auto_process"
    GITHUB_LAST_SYNC_KEY = "github_last_sync_result"
    OLLAMA_EXTRACTION_MODEL_KEY = "ollama_extraction_model"
    OLLAMA_EMBEDDING_MODEL_KEY = "ollama_embedding_model"

    def __init__(self, db: Session) -> None:
        self.db = db
        self.env_settings = get_settings()

    def get_inbox_folder(self) -> str:
        return self._get(self.INBOX_FOLDER_KEY, self.env_settings.inbox_folder)

    def set_inbox_folder(self, value: str) -> str:
        return self._set(self.INBOX_FOLDER_KEY, value.strip())

    def get_ollama_extraction_model(self) -> str:
        return self._get(self.OLLAMA_EXTRACTION_MODEL_KEY, self.env_settings.ollama_extraction_model)

    def set_ollama_extraction_model(self, value: str) -> str:
        return self._set(self.OLLAMA_EXTRACTION_MODEL_KEY, value.strip())

    def get_ollama_embedding_model(self) -> str:
        return self._get(self.OLLAMA_EMBEDDING_MODEL_KEY, self.env_settings.ollama_embedding_model)

    def set_ollama_embedding_model(self, value: str) -> str:
        return self._set(self.OLLAMA_EMBEDDING_MODEL_KEY, value.strip())

    def get_gmail_enabled(self) -> bool:
        return self._get_bool(self.GMAIL_ENABLED_KEY, self.env_settings.gmail_enabled)

    def set_gmail_enabled(self, value: bool) -> bool:
        self._set(self.GMAIL_ENABLED_KEY, str(value).lower())
        return value

    def get_gmail_label(self) -> str:
        return self._get(self.GMAIL_LABEL_KEY, self.env_settings.gmail_label)

    def set_gmail_label(self, value: str) -> str:
        return self._set(self.GMAIL_LABEL_KEY, value.strip())

    def get_gmail_query(self) -> str:
        return self._get(self.GMAIL_QUERY_KEY, self.env_settings.gmail_query)

    def set_gmail_query(self, value: str) -> str:
        return self._set(self.GMAIL_QUERY_KEY, value.strip())

    def get_gmail_auto_process(self) -> bool:
        return self._get_bool(self.GMAIL_AUTO_PROCESS_KEY, self.env_settings.gmail_auto_process)

    def set_gmail_auto_process(self, value: bool) -> bool:
        self._set(self.GMAIL_AUTO_PROCESS_KEY, str(value).lower())
        return value

    def get_gmail_last_sync_result(self) -> dict | None:
        value = self._get(self.GMAIL_LAST_SYNC_KEY, "")
        if not value:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None

    def set_gmail_last_sync_result(self, result: dict) -> dict:
        self._set(self.GMAIL_LAST_SYNC_KEY, json.dumps(result, default=str))
        return result

    def set_gmail_last_sync_error(self, error: str, query: str | None = None) -> dict:
        result = {
            "status": "failed",
            "query": query or self.get_gmail_query(),
            "synced_at": datetime.now(timezone.utc).isoformat(),
            "error": error,
            "imported_count": 0,
            "skipped_count": 0,
            "processed_count": 0,
            "failed_count": 1,
        }
        return self.set_gmail_last_sync_result(result)

    def get_gitlab_enabled(self) -> bool:
        return self._get_bool(self.GITLAB_ENABLED_KEY, False)

    def set_gitlab_enabled(self, value: bool) -> bool:
        self._set(self.GITLAB_ENABLED_KEY, str(value).lower())
        return value

    def get_gitlab_base_url(self) -> str:
        return self._get(self.GITLAB_BASE_URL_KEY, "https://gitlab.com")

    def set_gitlab_base_url(self, value: str) -> str:
        return self._set(self.GITLAB_BASE_URL_KEY, value.strip().rstrip("/") or "https://gitlab.com")

    def get_gitlab_token(self) -> str:
        return self._get(self.GITLAB_TOKEN_KEY, "")

    def set_gitlab_token(self, value: str) -> str:
        return self._set(self.GITLAB_TOKEN_KEY, value.strip())

    def get_gitlab_projects(self) -> str:
        return self._get(self.GITLAB_PROJECTS_KEY, "")

    def get_gitlab_project_paths(self) -> list[str]:
        raw_value = self.get_gitlab_projects().replace(",", "\n")
        return [line.strip() for line in raw_value.splitlines() if line.strip()]

    def set_gitlab_projects(self, value: str) -> str:
        return self._set(self.GITLAB_PROJECTS_KEY, value.strip())

    def get_gitlab_auto_process(self) -> bool:
        return self._get_bool(self.GITLAB_AUTO_PROCESS_KEY, True)

    def set_gitlab_auto_process(self, value: bool) -> bool:
        self._set(self.GITLAB_AUTO_PROCESS_KEY, str(value).lower())
        return value

    def get_gitlab_last_sync_result(self) -> dict | None:
        value = self._get(self.GITLAB_LAST_SYNC_KEY, "")
        if not value:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None

    def set_gitlab_last_sync_result(self, result: dict) -> dict:
        self._set(self.GITLAB_LAST_SYNC_KEY, json.dumps(result, default=str))
        return result

    def set_gitlab_last_sync_error(self, error: str) -> dict:
        result = {
            "status": "failed",
            "synced_at": datetime.now(timezone.utc).isoformat(),
            "error": error,
            "imported_count": 0,
            "skipped_count": 0,
            "queued_count": 0,
            "failed_count": 1,
        }
        return self.set_gitlab_last_sync_result(result)

    def get_github_enabled(self) -> bool:
        return self._get_bool(self.GITHUB_ENABLED_KEY, False)

    def set_github_enabled(self, value: bool) -> bool:
        self._set(self.GITHUB_ENABLED_KEY, str(value).lower())
        return value

    def get_github_token(self) -> str:
        return self._get(self.GITHUB_TOKEN_KEY, "")

    def set_github_token(self, value: str) -> str:
        return self._set(self.GITHUB_TOKEN_KEY, value.strip())

    def get_github_repositories(self) -> str:
        return self._get(self.GITHUB_REPOSITORIES_KEY, "")

    def get_github_repository_names(self) -> list[str]:
        raw_value = self.get_github_repositories().replace(",", "\n")
        return [line.strip() for line in raw_value.splitlines() if line.strip()]

    def set_github_repositories(self, value: str) -> str:
        return self._set(self.GITHUB_REPOSITORIES_KEY, value.strip())

    def get_github_auto_process(self) -> bool:
        return self._get_bool(self.GITHUB_AUTO_PROCESS_KEY, True)

    def set_github_auto_process(self, value: bool) -> bool:
        self._set(self.GITHUB_AUTO_PROCESS_KEY, str(value).lower())
        return value

    def get_github_last_sync_result(self) -> dict | None:
        value = self._get(self.GITHUB_LAST_SYNC_KEY, "")
        if not value:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None

    def set_github_last_sync_result(self, result: dict) -> dict:
        self._set(self.GITHUB_LAST_SYNC_KEY, json.dumps(result, default=str))
        return result

    def set_github_last_sync_error(self, error: str) -> dict:
        result = {
            "status": "failed",
            "synced_at": datetime.now(timezone.utc).isoformat(),
            "error": error,
            "imported_count": 0,
            "skipped_count": 0,
            "queued_count": 0,
            "failed_count": 1,
        }
        return self.set_github_last_sync_result(result)

    def _get(self, key: str, fallback: str) -> str:
        setting = self.db.get(AppSetting, key)
        return setting.value if setting else fallback

    def _get_bool(self, key: str, fallback: bool) -> bool:
        value = self._get(key, str(fallback).lower()).lower()
        return value in {"1", "true", "yes", "on"}

    def _set(self, key: str, value: str) -> str:
        setting = self.db.get(AppSetting, key)
        if setting:
            setting.value = value
        else:
            self.db.add(AppSetting(key=key, value=value))
        self.db.commit()
        return value

    def as_dict(self) -> dict:
        credentials_exists = self._path(self.env_settings.gmail_credentials_path).exists()
        token_exists = self._path(self.env_settings.gmail_token_path).exists()
        return {
            "ollama_base_url": self.env_settings.ollama_base_url,
            "ollama_extraction_model": self.get_ollama_extraction_model(),
            "ollama_embedding_model": self.get_ollama_embedding_model(),
            "inbox_folder": self.get_inbox_folder(),
            "gmail_enabled": self.get_gmail_enabled(),
            "gmail_label": self.get_gmail_label(),
            "gmail_query": self.get_gmail_query(),
            "gmail_auto_process": self.get_gmail_auto_process(),
            "gmail_credentials_path": self.env_settings.gmail_credentials_path,
            "gmail_token_path": self.env_settings.gmail_token_path,
            "gmail_credentials_exists": credentials_exists,
            "gmail_token_exists": token_exists,
            "gmail_status": self._gmail_status(credentials_exists, token_exists),
            "gmail_last_sync": self.get_gmail_last_sync_result(),
            "gitlab_enabled": self.get_gitlab_enabled(),
            "gitlab_base_url": self.get_gitlab_base_url(),
            "gitlab_projects": self.get_gitlab_projects(),
            "gitlab_auto_process": self.get_gitlab_auto_process(),
            "gitlab_token_configured": bool(self.get_gitlab_token()),
            "gitlab_status": self._gitlab_status(),
            "gitlab_last_sync": self.get_gitlab_last_sync_result(),
            "github_enabled": self.get_github_enabled(),
            "github_repositories": self.get_github_repositories(),
            "github_auto_process": self.get_github_auto_process(),
            "github_token_configured": bool(self.get_github_token()),
            "github_status": self._github_status(),
            "github_last_sync": self.get_github_last_sync_result(),
        }

    def _gmail_status(self, credentials_exists: bool, token_exists: bool) -> str:
        if not self.get_gmail_enabled():
            return "disabled"
        if not credentials_exists:
            return "missing_credentials"
        if not token_exists:
            return "needs_authorization"
        return "ready"

    def _gitlab_status(self) -> str:
        if not self.get_gitlab_enabled():
            return "disabled"
        if not self.get_gitlab_token():
            return "missing_token"
        if not self.get_gitlab_project_paths():
            return "missing_projects"
        return "ready"

    def _github_status(self) -> str:
        if not self.get_github_enabled():
            return "disabled"
        if not self.get_github_token():
            return "missing_token"
        if not self.get_github_repository_names():
            return "missing_repositories"
        return "ready"

    def _path(self, value: str) -> Path:
        path = Path(value).expanduser()
        if path.is_absolute():
            return path
        return (Path.cwd() / path).resolve()
