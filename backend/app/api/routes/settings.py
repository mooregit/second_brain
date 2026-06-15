from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsPatch(BaseModel):
    inbox_folder: str | None = None


@router.get("")
def get_app_settings(db: Session = Depends(get_db)) -> dict:
    return SettingsService(db).as_dict()


@router.patch("")
def patch_settings(payload: SettingsPatch, db: Session = Depends(get_db)) -> dict:
    service = SettingsService(db)
    if payload.inbox_folder is not None:
        service.set_inbox_folder(payload.inbox_folder)
    return service.as_dict()
