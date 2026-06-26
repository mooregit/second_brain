import asyncio
import hashlib

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

import pytest
from fastapi import BackgroundTasks, HTTPException

from app.api.routes import items as item_routes
from app.api.routes.items import get_item, list_items, upload_item
from app.core.database import Base
from app.models import FileAsset, Memory, ProcessingRun, RawItem, Tag
from app.services.book_brief_service import BookBriefService
from app.services.document_ingestion_service import DocumentIngestionService
from app.services.embedding_service import EmbeddingService
from app.services.file_service import FileService
from app.services.ollama_client import OllamaClient


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
    ("filename", "content_type", "expected_body"),
    [
        ("note.txt", "text/plain", "# Note\nUpload body"),
        ("note.md", "text/markdown", "# Note\nUpload body"),
    ],
)
def test_upload_item_stores_file_asset_and_original_content(
    db_session: Session,
    tmp_path,
    monkeypatch,
    filename: str,
    content_type: str,
    expected_body: str,
) -> None:
    monkeypatch.setattr(FileService, "_upload_directory", lambda self, raw_item_id: tmp_path / "uploads" / raw_item_id)
    content = b"# Note\nUpload body"
    file = FakeUploadFile(filename, content_type, content)

    item = asyncio.run(upload_item(BackgroundTasks(), file, db_session))
    asset = db_session.scalar(select(FileAsset).where(FileAsset.raw_item_id == item.id))

    assert isinstance(item, RawItem)
    assert item.source_type == "upload"
    assert item.body_text == expected_body
    assert item.source_uri.endswith(f"/{filename}")
    assert asset is not None
    assert asset.filename == filename
    assert asset.mime_type == content_type
    assert asset.size_bytes == len(content)
    assert asset.sha256 == hashlib.sha256(content).hexdigest()
    assert (tmp_path / "uploads" / item.id / filename).read_bytes() == content


def test_upload_item_stores_pdf_and_queues_background_text_extraction(db_session: Session, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(FileService, "_upload_directory", lambda self, raw_item_id: tmp_path / "uploads" / raw_item_id)
    monkeypatch.setattr(FileService, "extract_pdf_pages", lambda self, content: pytest.fail("PDF text extraction should run in the background"))
    content = b"%PDF-1.4 fake pdf content"
    file = FakeUploadFile("brief.pdf", "application/pdf", content)
    background_tasks = BackgroundTasks()

    item = asyncio.run(upload_item(background_tasks, file, db_session))
    asset = db_session.scalar(select(FileAsset).where(FileAsset.raw_item_id == item.id))
    chunks = db_session.scalars(select(RawItem).where(RawItem.source_type == "pdf_chunk")).all()

    assert item.title == "brief.pdf"
    assert item.status == "extracting"
    assert "Text extraction and chunking are queued" in item.body_text
    assert item.metadata_json["ingestion_status"] == "queued_text_extraction"
    assert item.content_type == "application/pdf"
    assert asset is not None
    assert asset.filename == "brief.pdf"
    assert asset.sha256 == hashlib.sha256(content).hexdigest()
    assert (tmp_path / "uploads" / item.id / "brief.pdf").read_bytes() == content
    assert chunks == []
    assert len(background_tasks.tasks) == 1
    assert list_items(db_session) == [item]


def test_document_ingestion_chunks_pdf_and_queues_each_chunk(db_session: Session, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(FileService, "_upload_directory", lambda self, raw_item_id: tmp_path / "uploads" / raw_item_id)
    monkeypatch.setattr(
        FileService,
        "extract_pdf_pages",
        lambda self, content: [
            {"page_number": 1, "text": "Algorithms and data structures"},
            {"page_number": 2, "text": "Machine learning and neural networks"},
        ],
    )
    item = RawItem(
        source_type="upload",
        title="brief.pdf",
        body_text="PDF uploaded for long-document processing.",
        content_type="application/pdf",
        status="extracting",
        metadata_json={"filename": "brief.pdf", "ingestion_status": "queued_text_extraction"},
    )
    db_session.add(item)
    db_session.flush()
    asset = FileService(db_session).store_upload(item.id, "brief.pdf", b"%PDF-1.4 fake pdf content", "application/pdf")
    db_session.commit()

    run_ids = DocumentIngestionService(db_session).chunk_pdf_upload(item, asset)
    db_session.refresh(item)
    chunks = db_session.scalars(select(RawItem).where(RawItem.source_type == "pdf_chunk")).all()
    runs = db_session.scalars(select(ProcessingRun).where(ProcessingRun.raw_item_id.in_([chunk.id for chunk in chunks]))).all()

    assert item.status == "chunked"
    assert "PDF imported for long-document processing" in item.body_text
    assert item.metadata_json["ingestion_status"] == "chunked"
    assert item.metadata_json["document_chunk_count"] == 1
    assert item.metadata_json["queued_chunk_run_ids"] == run_ids
    assert len(chunks) == 1
    assert chunks[0].status == "pending"
    assert chunks[0].metadata_json["parent_raw_item_id"] == item.id
    assert chunks[0].metadata_json["page_start"] == 1
    assert chunks[0].metadata_json["page_end"] == 2
    assert "Source pages: pages 1-2" in chunks[0].body_text
    assert len(runs) == 1
    assert runs[0].status == "pending"
    assert list_items(db_session) == [item]
    detail = get_item(item.id, db_session)
    assert len(detail["document_chunks"]) == 1
    assert detail["document_chunks"][0]["item"]["id"] == chunks[0].id
    assert detail["document_chunks"][0]["latest_processing_run"]["status"] == "pending"


def test_book_brief_requires_completed_chunk_memories(db_session: Session) -> None:
    parent = RawItem(source_type="upload", title="book.pdf", body_text="PDF", content_type="application/pdf", status="chunked")
    db_session.add(parent)
    db_session.flush()
    db_session.add(
        RawItem(
            source_type="pdf_chunk",
            title="book.pdf pages 1-8",
            body_text="Chunk",
            status="pending",
            metadata_json={"parent_raw_item_id": parent.id, "page_start": 1, "page_end": 8},
        )
    )
    db_session.commit()

    with pytest.raises(ValueError, match="requires all chunks"):
        BookBriefService(db_session).create_run(parent.id)


def test_book_brief_generates_parent_memory_from_chunk_memories(db_session: Session, monkeypatch) -> None:
    async def fake_generate(self, model: str, prompt: str) -> str:
        assert "Algorithms and Data Structures" in prompt
        assert "pages 1-8" in prompt
        return """
        {
          "summary": "Book Brief: The book explains core algorithmic strategies including data structures, sorting, search, and practical tradeoffs.",
          "memory_type": "resource",
          "projects": [],
          "people": [],
          "tasks": [],
          "ideas": ["Use algorithm families as reusable problem-solving patterns."],
          "decisions": [],
          "open_questions": ["Which algorithms should be practiced first?"],
          "tags": ["algorithms", "data structures"],
          "entities": ["binary search", "merge sort"],
          "relationships": [
            {"source": "binary search", "target": "data structures", "relationship": "relates_to"}
          ],
          "suggested_actions": [],
          "confidence": 0.92
        }
        """

    async def fake_embed_owner(self, owner_type: str, owner_id: str, text: str) -> None:
        return None

    monkeypatch.setattr(OllamaClient, "generate", fake_generate)
    monkeypatch.setattr(EmbeddingService, "embed_owner", fake_embed_owner)
    parent = RawItem(source_type="upload", title="book.pdf", body_text="PDF", content_type="application/pdf", status="chunked")
    db_session.add(parent)
    db_session.flush()
    chunk = RawItem(
        source_type="pdf_chunk",
        title="book.pdf pages 1-8",
        body_text="Chunk",
        status="processed",
        metadata_json={"parent_raw_item_id": parent.id, "chunk_index": 1, "page_start": 1, "page_end": 8},
    )
    db_session.add(chunk)
    db_session.flush()
    chunk_memory = Memory(
        raw_item_id=chunk.id,
        memory_type="note",
        summary="Algorithms and Data Structures: binary search and merge sort.",
        confidence=0.8,
        validated_json={},
        raw_llm_output="{}",
    )
    tag = Tag(name="algorithms")
    db_session.add_all([chunk_memory, tag])
    db_session.flush()
    chunk_memory.tags.append(tag)
    db_session.commit()

    run = BookBriefService(db_session).create_run(parent.id)
    memory = asyncio.run(BookBriefService(db_session).process_run(run.id))
    detail = get_item(parent.id, db_session)

    assert memory.raw_item_id == parent.id
    assert memory.memory_type == "resource"
    assert memory.validated_json["source"] == "book_brief"
    assert memory.validated_json["chunk_count"] == 1
    assert "Book Brief" in [tag.name for tag in memory.tags]
    assert db_session.get(ProcessingRun, run.id).status == "succeeded"
    assert db_session.get(RawItem, parent.id).metadata_json["book_brief_memory_id"] == memory.id
    assert len(detail["memories"]) == 1
    assert detail["memories"][0]["id"] == memory.id


def test_book_brief_repairs_non_json_model_output(db_session: Session, monkeypatch) -> None:
    responses = iter(
        [
            "Here is the book brief in prose, not JSON.",
            """
            {
              "summary": "Book Brief: Repaired synthesis about algorithms.",
              "memory_type": "resource",
              "projects": [],
              "people": [],
              "tasks": [],
              "ideas": ["Practice algorithms by category."],
              "decisions": [],
              "open_questions": [],
              "tags": ["algorithms"],
              "entities": ["binary search"],
              "relationships": [],
              "suggested_actions": [],
              "confidence": 0.7
            }
            """,
        ]
    )

    async def fake_generate(self, model: str, prompt: str) -> str:
        return next(responses)

    async def fake_embed_owner(self, owner_type: str, owner_id: str, text: str) -> None:
        return None

    monkeypatch.setattr(OllamaClient, "generate", fake_generate)
    monkeypatch.setattr(EmbeddingService, "embed_owner", fake_embed_owner)
    parent = RawItem(source_type="upload", title="book.pdf", body_text="PDF", content_type="application/pdf", status="chunked")
    db_session.add(parent)
    db_session.flush()
    chunk = RawItem(
        source_type="pdf_chunk",
        title="book.pdf pages 1-8",
        body_text="Chunk",
        status="processed",
        metadata_json={"parent_raw_item_id": parent.id, "chunk_index": 1, "page_start": 1, "page_end": 8},
    )
    db_session.add(chunk)
    db_session.flush()
    db_session.add(
        Memory(
            raw_item_id=chunk.id,
            memory_type="note",
            summary="Algorithms and Data Structures: binary search.",
            confidence=0.8,
            validated_json={},
            raw_llm_output="{}",
        )
    )
    db_session.commit()

    run = BookBriefService(db_session).create_run(parent.id)
    memory = asyncio.run(BookBriefService(db_session).process_run(run.id))
    db_session.refresh(run)

    assert memory.summary == "Book Brief: Repaired synthesis about algorithms."
    assert run.status == "succeeded"
    assert "--- repaired ---" in (run.raw_output or "")


def test_upload_item_rejects_files_over_configured_limit(db_session: Session, monkeypatch) -> None:
    class UploadSettings:
        max_upload_bytes = 4

    monkeypatch.setattr(item_routes, "get_settings", lambda: UploadSettings())
    file = FakeUploadFile("large.pdf", "application/pdf", b"12345")

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(upload_item(BackgroundTasks(), file, db_session))

    assert exc_info.value.status_code == 413
    assert "Maximum upload size is 4 bytes" in exc_info.value.detail
    assert db_session.scalars(select(RawItem)).all() == []


class FakeUploadFile:
    def __init__(self, filename: str, content_type: str, content: bytes) -> None:
        self.filename = filename
        self.content_type = content_type
        self._content = content

    async def read(self) -> bytes:
        return self._content
