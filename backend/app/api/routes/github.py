from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.raw_item import RawItemOut
from app.services.github_service import GitHubService
from app.services.processing_queue_service import process_queued_run
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/github", tags=["github"])


class GitHubSyncRequest(BaseModel):
    max_results: int = Field(default=20, ge=1, le=100)
    auto_process: bool | None = None


@router.get("/status")
def github_status(db: Session = Depends(get_db)) -> dict:
    settings = SettingsService(db)
    return {
        "enabled": settings.get_github_enabled(),
        "repositories": settings.get_github_repository_names(),
        "auto_process": settings.get_github_auto_process(),
        "token_configured": bool(settings.get_github_token()),
        "status": settings.as_dict()["github_status"],
        "last_sync": settings.get_github_last_sync_result(),
    }


@router.post("/sync")
async def sync_github(background_tasks: BackgroundTasks, payload: GitHubSyncRequest | None = None, db: Session = Depends(get_db)) -> dict:
    payload = payload or GitHubSyncRequest()
    try:
        result = await GitHubService(db).sync(max_results=payload.max_results, auto_process=payload.auto_process)
    except RuntimeError as exc:
        SettingsService(db).set_github_last_sync_error(str(exc))
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    for run_id in result.get("queued_run_ids", []):
        background_tasks.add_task(process_queued_run, run_id)
    return {
        "status": result["status"],
        "repositories": result["repositories"],
        "auto_process": result["auto_process"],
        "max_results": result["max_results"],
        "synced_at": result["synced_at"],
        "imported_count": result["imported_count"],
        "skipped_count": result["skipped_count"],
        "queued_count": result["queued_count"],
        "failed_count": result["failed_count"],
        "imported_items": [RawItemOut.model_validate(item).model_dump(mode="json") for item in result["imported_items"]],
        "skipped_source_uris": result["skipped_source_uris"],
        "queued_item_ids": result["queued_item_ids"],
        "queued_run_ids": result["queued_run_ids"],
        "failures": result["failures"],
    }
