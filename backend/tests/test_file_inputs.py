from collections.abc import Generator

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.models import RawItem
from app.services.file_service import FileService
from app.services.settings_service import SettingsService


@pytest.fixture
def db_session(tmp_path) -> Generator[Session, None, None]:
    engine = create_engine(f"sqlite:///{tmp_path}/test.db", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine)


def test_scan_inbox_folder_imports_supported_files_once(db_session: Session, tmp_path, monkeypatch) -> None:
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "note.md").write_text("# Note\n\nRemember this.", encoding="utf-8")
    (inbox / "brief.pdf").write_bytes(b"%PDF-1.4 fake pdf content")
    monkeypatch.setattr(FileService, "extract_pdf_text", lambda self, content: "PDF body")
    SettingsService(db_session).set_inbox_folder(str(inbox))

    first_scan = FileService(db_session).scan_inbox_folder()
    assert first_scan["created_count"] == 2
    assert first_scan["skipped_count"] == 0

    items = db_session.scalars(select(RawItem).where(RawItem.source_type == "folder").order_by(RawItem.title)).all()
    assert [item.title for item in items] == ["brief", "note"]
    assert items[0].body_text == "PDF body"
    assert items[0].content_type == "application/pdf"
    assert items[1].body_text.startswith("# Note")

    second_scan = FileService(db_session).scan_inbox_folder()
    assert second_scan["created_count"] == 0
    assert second_scan["skipped_count"] == 2
