from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("")
def get_app_settings() -> dict:
    settings = get_settings()
    return {
        "ollama_base_url": settings.ollama_base_url,
        "ollama_extraction_model": settings.ollama_extraction_model,
        "ollama_embedding_model": settings.ollama_embedding_model,
        "inbox_folder": settings.inbox_folder,
        "gmail_status": "deferred",
    }


@router.patch("")
def patch_settings() -> dict:
    return {"status": "settings are environment-backed in the MVP"}

