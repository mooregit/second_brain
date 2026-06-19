from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.raw_item import RawItemOut
from app.services.draft_reply_service import DraftReplyService
from app.services.gmail_service import GmailService
from app.services.processing_queue_service import process_queued_run
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/gmail", tags=["gmail"])


class GmailSyncRequest(BaseModel):
    max_results: int = Field(default=10, ge=1, le=100)
    auto_process: bool | None = None


class DraftReplyRequest(BaseModel):
    email_message_id: str
    create_in_gmail: bool = True


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
async def sync_gmail(background_tasks: BackgroundTasks, payload: GmailSyncRequest | None = None, db: Session = Depends(get_db)) -> dict:
    payload = payload or GmailSyncRequest()
    try:
        result = await GmailService(db).sync(max_results=payload.max_results, auto_process=payload.auto_process)
    except RuntimeError as exc:
        SettingsService(db).set_gmail_last_sync_error(str(exc))
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    for run_id in result.get("queued_run_ids", []):
        background_tasks.add_task(process_queued_run, run_id)
    return {
        "status": result["status"],
        "query": result["query"],
        "auto_process": result["auto_process"],
        "max_results": result["max_results"],
        "synced_at": result["synced_at"],
        "imported_count": result["imported_count"],
        "skipped_count": result["skipped_count"],
        "processed_count": result["processed_count"],
        "queued_count": result["queued_count"],
        "failed_count": result["failed_count"],
        "imported_items": [RawItemOut.model_validate(item).model_dump(mode="json") for item in result["imported_items"]],
        "skipped_message_ids": result["skipped_message_ids"],
        "processed_item_ids": result["processed_item_ids"],
        "queued_item_ids": result["queued_item_ids"],
        "queued_run_ids": result["queued_run_ids"],
        "failures": result["failures"],
    }


@router.post("/draft-reply")
async def draft_reply(payload: DraftReplyRequest, db: Session = Depends(get_db)) -> dict:
    try:
        draft = await DraftReplyService(db).create_draft_reply(
            payload.email_message_id,
            create_in_gmail=payload.create_in_gmail,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "id": draft.id,
        "email_message_id": draft.email_message_id,
        "body": draft.body,
        "status": draft.status,
        "gmail_draft_id": draft.gmail_draft_id,
        "created_at": draft.created_at.isoformat(),
    }
