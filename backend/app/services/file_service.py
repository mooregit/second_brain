import hashlib
from pathlib import Path
from re import sub

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import FileAsset, RawItem
from app.services.settings_service import SettingsService


class FileService:
    supported_suffixes = {".txt", ".md"}

    def __init__(self, db: Session) -> None:
        self.db = db

    def store_upload(self, raw_item_id: str, filename: str, content: bytes, mime_type: str | None) -> FileAsset:
        directory = self._upload_directory(raw_item_id)
        directory.mkdir(parents=True, exist_ok=True)
        safe_filename = self._safe_filename(filename)
        path = directory / safe_filename
        path.write_bytes(content)
        asset = FileAsset(
            raw_item_id=raw_item_id,
            filename=safe_filename,
            stored_path=str(path),
            mime_type=mime_type,
            size_bytes=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
        )
        self.db.add(asset)
        return asset

    def scan_inbox_folder(self) -> dict:
        folder = Path(SettingsService(self.db).get_inbox_folder()).expanduser()
        if not folder.is_absolute():
            folder = Path.cwd() / folder
        folder = folder.resolve()
        if not folder.exists():
            folder.mkdir(parents=True, exist_ok=True)
        if not folder.is_dir():
            raise ValueError(f"Inbox folder is not a directory: {folder}")

        created: list[RawItem] = []
        skipped: list[str] = []
        for path in sorted(folder.iterdir()):
            if not path.is_file() or path.suffix.lower() not in self.supported_suffixes:
                continue
            source_uri = str(path)
            if self.db.scalar(select(RawItem).where(RawItem.source_uri == source_uri)):
                skipped.append(path.name)
                continue
            body_text = path.read_text(encoding="utf-8")
            item = RawItem(
                source_type="folder",
                title=path.stem,
                body_text=body_text,
                content_type="text/markdown" if path.suffix.lower() == ".md" else "text/plain",
                source_uri=source_uri,
                metadata_json={"filename": path.name, "folder": str(folder)},
            )
            self.db.add(item)
            created.append(item)
        self.db.commit()
        for item in created:
            self.db.refresh(item)
        return {
            "folder": str(folder),
            "created_count": len(created),
            "skipped_count": len(skipped),
            "created_items": created,
            "skipped_files": skipped,
        }

    def _upload_directory(self, raw_item_id: str) -> Path:
        folder = Path(get_settings().uploads_folder).expanduser()
        if not folder.is_absolute():
            folder = Path.cwd() / folder
        return (folder / "manual" / raw_item_id).resolve()

    def _safe_filename(self, value: str) -> str:
        cleaned = sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
        return cleaned.strip("._") or "upload.txt"
