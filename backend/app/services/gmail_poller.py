from collections.abc import Callable
from threading import Event

from sqlalchemy.orm import Session

from app.services.gmail_service import GmailService
from app.services.settings_service import SettingsService


class GmailPoller:
    def __init__(self, db_factory: Callable[[], Session], interval_seconds: float = 300.0, max_results: int = 10) -> None:
        self.db_factory = db_factory
        self.interval_seconds = interval_seconds
        self.max_results = max_results

    async def poll_once(self) -> dict:
        db = self.db_factory()
        try:
            settings = SettingsService(db)
            if not settings.get_gmail_enabled():
                return {"status": "disabled", "synced": False}
            result = await GmailService(db).sync(max_results=self.max_results)
            return {"status": result["status"], "synced": True, **{key: value for key, value in result.items() if key != "imported_items"}}
        finally:
            db.close()

    async def watch(self, stop_event: Event | None = None) -> None:
        stop_event = stop_event or Event()
        while not stop_event.is_set():
            await self.poll_once()
            stop_event.wait(self.interval_seconds)
