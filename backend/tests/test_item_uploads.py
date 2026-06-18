import asyncio
import hashlib

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

import pytest

from app.api.routes.items import upload_item
from app.core.database import Base
from app.models import FileAsset, RawItem
from app.services.file_service import FileService


@pytest.fixture
def db_session(tmp_path) -> Session:
    engine = create_engine(f"sqlite:///{tmp_path}/test.db", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine)


@pytest.mark.parametrize(
    ("filename", "content_type"),
    [
        ("note.txt", "text/plain"),
        ("note.md", "text/markdown"),
    ],
)
def test_upload_item_stores_file_asset_and_original_content(db_session: Session, tmp_path, monkeypatch, filename: str, content_type: str) -> None:
    monkeypatch.setattr(FileService, "_upload_directory", lambda self, raw_item_id: tmp_path / "uploads" / raw_item_id)
    content = b"# Note\nUpload body"
    file = FakeUploadFile(filename, content_type, content)

    item = asyncio.run(upload_item(file, db_session))
    asset = db_session.scalar(select(FileAsset).where(FileAsset.raw_item_id == item.id))

    assert isinstance(item, RawItem)
    assert item.source_type == "upload"
    assert item.body_text == "# Note\nUpload body"
    assert item.source_uri.endswith(f"/{filename}")
    assert asset is not None
    assert asset.filename == filename
    assert asset.mime_type == content_type
    assert asset.size_bytes == len(content)
    assert asset.sha256 == hashlib.sha256(content).hexdigest()
    assert (tmp_path / "uploads" / item.id / filename).read_bytes() == content


class FakeUploadFile:
    def __init__(self, filename: str, content_type: str, content: bytes) -> None:
        self.filename = filename
        self.content_type = content_type
        self._content = content

    async def read(self) -> bytes:
        return self._content
