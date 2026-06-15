from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import AppSetting


class SettingsService:
    INBOX_FOLDER_KEY = "inbox_folder"

    def __init__(self, db: Session) -> None:
        self.db = db
        self.env_settings = get_settings()

    def get_inbox_folder(self) -> str:
        setting = self.db.get(AppSetting, self.INBOX_FOLDER_KEY)
        return setting.value if setting else self.env_settings.inbox_folder

    def set_inbox_folder(self, value: str) -> str:
        normalized = value.strip()
        setting = self.db.get(AppSetting, self.INBOX_FOLDER_KEY)
        if setting:
            setting.value = normalized
        else:
            self.db.add(AppSetting(key=self.INBOX_FOLDER_KEY, value=normalized))
        self.db.commit()
        return normalized

    def as_dict(self) -> dict:
        return {
            "ollama_base_url": self.env_settings.ollama_base_url,
            "ollama_extraction_model": self.env_settings.ollama_extraction_model,
            "ollama_embedding_model": self.env_settings.ollama_embedding_model,
            "inbox_folder": self.get_inbox_folder(),
            "gmail_status": "deferred",
        }
