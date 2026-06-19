from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.raw_item import RawItemOut
from app.services.gmail_service import GmailService
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/gmail", tags=["gmail"])


class GmailSyncRequest(BaseModel):
    max_results: int = Field(default=10, ge=1, le=100)
    auto_process: bool | None = None


@router.get("/status")
def gmail_status(db: Session = Depends(get_db)) -> dict:
    settings = SettingsService(db)
    return {
        "enabled": settings.get_gmail_enabled(),
        "query": settings.get_gmail_query(),
        "label": settings.get_gmail_label(),
        "auto_process": settings.get_gmail_auto_process(),
        "credentials_path": settings.env_settings.gmail_credentials_path,
        "token_path": settings.env_settings.gmail_token_path,
        "credentials_exists": settings.as_dict()["gmail_credentials_exists"],
        "token_exists": settings.as_dict()["gmail_token_exists"],
        "status": settings.as_dict()["gmail_status"],
        "last_sync": settings.get_gmail_last_sync_result(),
    }


@router.post("/sync")
async def sync_gmail(payload: GmailSyncRequest | None = None, db: Session = Depends(get_db)) -> dict:
    payload = payload or GmailSyncRequest()
    try:
        result = await GmailService(db).sync(max_results=payload.max_results, auto_process=payload.auto_process)
    except RuntimeError as exc:
        SettingsService(db).set_gmail_last_sync_error(str(exc))
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "status": result["status"],
        "query": result["query"],
        "auto_process": result["auto_process"],
        "max_results": result["max_results"],
        "synced_at": result["synced_at"],
        "imported_count": result["imported_count"],
        "skipped_count": result["skipped_count"],
        "processed_count": result["processed_count"],
        "failed_count": result["failed_count"],
        "imported_items": [RawItemOut.model_validate(item).model_dump(mode="json") for item in result["imported_items"]],
        "skipped_message_ids": result["skipped_message_ids"],
        "processed_item_ids": result["processed_item_ids"],
        "failures": result["failures"],
    }


@router.post("/draft-reply")
def draft_reply() -> dict:
    return {"status": "deferred", "detail": "Draft replies are planned and will never auto-send in the MVP."}
