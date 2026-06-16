from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsPatch(BaseModel):
    inbox_folder: str | None = None
    gmail_enabled: bool | None = None
    gmail_label: str | None = None
    gmail_query: str | None = None
    gmail_auto_process: bool | None = None


@router.get("")
def get_app_settings(db: Session = Depends(get_db)) -> dict:
    return SettingsService(db).as_dict()


@router.patch("")
def patch_settings(payload: SettingsPatch, db: Session = Depends(get_db)) -> dict:
    service = SettingsService(db)
    if payload.inbox_folder is not None:
        service.set_inbox_folder(payload.inbox_folder)
    if payload.gmail_enabled is not None:
        service.set_gmail_enabled(payload.gmail_enabled)
    if payload.gmail_label is not None:
        service.set_gmail_label(payload.gmail_label)
    if payload.gmail_query is not None:
        service.set_gmail_query(payload.gmail_query)
    if payload.gmail_auto_process is not None:
        service.set_gmail_auto_process(payload.gmail_auto_process)
    return service.as_dict()
