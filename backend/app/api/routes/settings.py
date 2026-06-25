from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.settings_service import SettingsService
from app.services.ollama_client import OllamaClient

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsPatch(BaseModel):
    inbox_folder: str | None = None
    ollama_extraction_model: str | None = None
    ollama_embedding_model: str | None = None
    gmail_enabled: bool | None = None
    gmail_label: str | None = None
    gmail_query: str | None = None
    gmail_auto_process: bool | None = None
    gitlab_enabled: bool | None = None
    gitlab_base_url: str | None = None
    gitlab_token: str | None = None
    gitlab_projects: str | None = None
    gitlab_auto_process: bool | None = None
    github_enabled: bool | None = None
    github_token: str | None = None
    github_repositories: str | None = None
    github_auto_process: bool | None = None


@router.get("")
def get_app_settings(db: Session = Depends(get_db)) -> dict:
    return SettingsService(db).as_dict()


@router.patch("")
def patch_settings(payload: SettingsPatch, db: Session = Depends(get_db)) -> dict:
    service = SettingsService(db)
    if payload.inbox_folder is not None:
        service.set_inbox_folder(payload.inbox_folder)
    if payload.ollama_extraction_model is not None:
        service.set_ollama_extraction_model(payload.ollama_extraction_model)
    if payload.ollama_embedding_model is not None:
        service.set_ollama_embedding_model(payload.ollama_embedding_model)
    if payload.gmail_enabled is not None:
        service.set_gmail_enabled(payload.gmail_enabled)
    if payload.gmail_label is not None:
        service.set_gmail_label(payload.gmail_label)
    if payload.gmail_query is not None:
        service.set_gmail_query(payload.gmail_query)
    if payload.gmail_auto_process is not None:
        service.set_gmail_auto_process(payload.gmail_auto_process)
    if payload.gitlab_enabled is not None:
        service.set_gitlab_enabled(payload.gitlab_enabled)
    if payload.gitlab_base_url is not None:
        service.set_gitlab_base_url(payload.gitlab_base_url)
    if payload.gitlab_token is not None:
        service.set_gitlab_token(payload.gitlab_token)
    if payload.gitlab_projects is not None:
        service.set_gitlab_projects(payload.gitlab_projects)
    if payload.gitlab_auto_process is not None:
        service.set_gitlab_auto_process(payload.gitlab_auto_process)
    if payload.github_enabled is not None:
        service.set_github_enabled(payload.github_enabled)
    if payload.github_token is not None:
        service.set_github_token(payload.github_token)
    if payload.github_repositories is not None:
        service.set_github_repositories(payload.github_repositories)
    if payload.github_auto_process is not None:
        service.set_github_auto_process(payload.github_auto_process)
    return service.as_dict()


@router.get("/ollama/models")
async def list_ollama_models() -> dict:
    try:
        models = await OllamaClient().list_models()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Could not list Ollama models: {exc}") from exc
    return {
        "models": models,
        "completion_models": [model for model in models if model["supports_completion"]],
        "embedding_models": [model for model in models if model["supports_embedding"]],
    }
