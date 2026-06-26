from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import FileAsset, RawItem
from app.services.file_service import DocumentChunk, FileService, PdfPage
from app.services.processing_queue_service import ProcessingQueueService


class DocumentIngestionService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def chunk_pdf_upload(self, parent: RawItem, asset: FileAsset) -> list[str]:
        if self._existing_chunks(parent.id):
            return []

        parent.status = "extracting"
        parent.metadata_json = {**(parent.metadata_json or {}), "ingestion_status": "extracting_text"}
        self.db.commit()

        try:
            content = Path(asset.stored_path).read_bytes()
            pages = FileService(self.db).extract_pdf_pages(content)
            chunks = FileService(self.db).chunk_pdf_pages(pages)
            run_ids = self._create_pdf_chunk_items(parent, asset, chunks)
        except Exception as exc:
            parent.status = "failed"
            parent.body_text = f"PDF text extraction failed for {asset.filename}: {exc}"
            parent.metadata_json = {**(parent.metadata_json or {}), "ingestion_status": "failed", "ingestion_error": str(exc)}
            self.db.commit()
            raise

        parent.body_text = render_pdf_parent_body(asset.filename, pages, chunks)
        parent.status = "chunked"
        parent.metadata_json = {
            **(parent.metadata_json or {}),
            "ingestion_status": "chunked",
            "document_chunk_count": len(chunks),
            "queued_chunk_run_ids": run_ids,
        }
        self.db.commit()
        return run_ids

    def _create_pdf_chunk_items(self, parent: RawItem, asset: FileAsset, chunks: list[DocumentChunk]) -> list[str]:
        run_ids: list[str] = []
        for chunk in chunks:
            page_start = chunk["page_start"]
            page_end = chunk["page_end"]
            page_label = f"page {page_start}" if page_start == page_end else f"pages {page_start}-{page_end}"
            chunk_item = RawItem(
                source_type="pdf_chunk",
                title=f"{parent.title} {page_label}",
                body_text=(
                    f"PDF chunk from {parent.title}\n"
                    f"Parent raw_item_id: {parent.id}\n"
                    f"Source pages: {page_label}\n\n"
                    f"{chunk['text']}"
                ),
                content_type="text/plain",
                source_uri=asset.stored_path,
                metadata_json={
                    "parent_raw_item_id": parent.id,
                    "file_asset_id": asset.id,
                    "filename": asset.filename,
                    "chunk_index": chunk["chunk_index"],
                    "page_start": page_start,
                    "page_end": page_end,
                    "chunk_count": len(chunks),
                },
            )
            self.db.add(chunk_item)
            self.db.flush()
            run = ProcessingQueueService(self.db).enqueue_item(chunk_item.id)
            run_ids.append(run.id)
        return run_ids

    def _existing_chunks(self, parent_raw_item_id: str) -> list[RawItem]:
        chunks = self.db.scalars(select(RawItem).where(RawItem.source_type == "pdf_chunk")).all()
        return [chunk for chunk in chunks if (chunk.metadata_json or {}).get("parent_raw_item_id") == parent_raw_item_id]


def render_pdf_parent_body(filename: str, pages: list[PdfPage], chunks: list[DocumentChunk]) -> str:
    return (
        f"PDF imported for long-document processing: {filename}\n\n"
        f"Selectable text pages: {len(pages)}\n"
        f"Queued chunks: {len(chunks)}\n\n"
        "Each chunk is stored as a source-linked PDF chunk item with page metadata and queued for extraction."
    )


async def process_pdf_upload_chunks(raw_item_id: str, file_asset_id: str) -> None:
    db = SessionLocal()
    try:
        parent = db.get(RawItem, raw_item_id)
        asset = db.get(FileAsset, file_asset_id)
        if not parent or not asset:
            return
        DocumentIngestionService(db).chunk_pdf_upload(parent, asset)
    finally:
        db.close()
