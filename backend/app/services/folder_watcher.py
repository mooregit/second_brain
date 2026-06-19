from collections.abc import Callable
from threading import Event
from time import sleep

from sqlalchemy.orm import Session

from app.services.file_service import FileService


class FolderWatcher:
    """Polls the configured inbox folder and imports supported files."""

    def __init__(self, db_factory: Callable[[], Session], interval_seconds: float = 30.0) -> None:
        self.db_factory = db_factory
        self.interval_seconds = interval_seconds

    def scan_once(self) -> dict:
        db = self.db_factory()
        try:
            return FileService(db).scan_inbox_folder()
        finally:
            db.close()

    def watch(self, stop_event: Event | None = None) -> None:
        stop_event = stop_event or Event()
        while not stop_event.is_set():
            self.scan_once()
            stop_event.wait(self.interval_seconds)
