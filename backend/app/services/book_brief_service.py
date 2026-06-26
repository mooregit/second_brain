import json
from datetime import datetime

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models import Memory, ProcessingRun, RawItem
from app.schemas.extraction import ExtractionResult
from app.services.extraction_service import ExtractionService
from app.services.ollama_client import OllamaClient
from app.services.settings_service import SettingsService


BOOK_BRIEF_PROMPT_VERSION = "book_brief_v1"


class BookBriefService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()
        self.app_settings = SettingsService(db)
        self.ollama = OllamaClient()

    def create_run(self, parent_raw_item_id: str, force: bool = False) -> ProcessingRun:
        parent = self.db.get(RawItem, parent_raw_item_id)
        if not parent:
            raise ValueError("Parent item not found")
        if parent.content_type != "application/pdf" and not self._document_chunks(parent.id):
            raise ValueError("Book Briefs can only be generated for chunked document items")
        if self._existing_book_brief(parent.id) and not force:
            raise ValueError("Book Brief already exists for this document")
        self._require_completed_chunks(parent.id)

        run = ProcessingRun(
            raw_item_id=parent.id,
            status="pending",
            model=self.app_settings.get_ollama_extraction_model(),
            prompt_version=BOOK_BRIEF_PROMPT_VERSION,
        )
        self.db.add(run)
        parent.metadata_json = {**(parent.metadata_json or {}), "book_brief_status": "pending", "book_brief_run_id": run.id}
        self.db.commit()
        self.db.refresh(run)
        return run

    async def process_run(self, run_id: str) -> Memory:
        run = self.db.get(ProcessingRun, run_id)
        if not run:
            raise ValueError("Book Brief run not found")
        parent = self.db.get(RawItem, run.raw_item_id)
        if not parent:
            raise ValueError("Parent item not found")

        run.status = "processing"
        run.started_at = datetime.utcnow()
        run.finished_at = None
        run.error = None
        parent.metadata_json = {**(parent.metadata_json or {}), "book_brief_status": "processing", "book_brief_run_id": run.id}
        self.db.commit()

        raw_output = ""
        extraction = ExtractionService(self.db)
        try:
            chunks = self._document_chunks(parent.id)
            self._require_completed_chunks(parent.id, chunks)
            prompt = self._build_prompt(parent, chunks)
            raw_output = await self.ollama.generate(run.model, prompt)
            result, raw_output = await self._parse_result(parent, raw_output, extraction, run.model)
            existing = self._existing_book_brief(parent.id)
            if existing:
                run.status = "succeeded"
                run.finished_at = datetime.utcnow()
                run.raw_output = raw_output
                run.parsed_json = existing.validated_json
                parent.metadata_json = {
                    **(parent.metadata_json or {}),
                    "book_brief_status": "succeeded",
                    "book_brief_run_id": run.id,
                    "book_brief_memory_id": existing.id,
                }
                self.db.commit()
                return existing
            result = self._tag_result_as_book_brief(result)
            memory = extraction._persist_result(parent, result, raw_output)
            memory.validated_json = {
                **result.model_dump(mode="json"),
                "source": "book_brief",
                "chunk_count": len(chunks),
                "chunk_memory_count": sum(len(self._chunk_memories(chunk)) for chunk in chunks),
            }
            run.status = "succeeded"
            run.finished_at = datetime.utcnow()
            run.raw_output = raw_output
            run.parsed_json = memory.validated_json
            parent.status = "processed"
            parent.metadata_json = {
                **(parent.metadata_json or {}),
                "book_brief_status": "succeeded",
                "book_brief_run_id": run.id,
                "book_brief_memory_id": memory.id,
            }
            self.db.commit()
            self.db.refresh(memory)
            await extraction._embed_records(memory)
            return memory
        except Exception as exc:
            run.status = "failed"
            run.finished_at = datetime.utcnow()
            run.error = str(exc)
            run.raw_output = raw_output
            parent.metadata_json = {**(parent.metadata_json or {}), "book_brief_status": "failed", "book_brief_run_id": run.id}
            self.db.commit()
            raise

    async def _parse_result(self, parent: RawItem, raw_output: str, extraction: ExtractionService, model: str) -> tuple[ExtractionResult, str]:
        try:
            parsed = extraction._normalize_extraction_payload(extraction._parse_extraction_output(raw_output), parent.title)
            return ExtractionResult.model_validate(parsed), raw_output
        except (json.JSONDecodeError, ValidationError) as exc:
            repair_prompt = (
                self._prompt("extraction_repair.md")
                .replace("{{validation_error}}", str(exc))
                .replace("{{invalid_output}}", raw_output)
            )
            repaired_output = await self.ollama.generate(model, repair_prompt)
            parsed = extraction._normalize_extraction_payload(extraction._parse_extraction_output(repaired_output), parent.title)
            return ExtractionResult.model_validate(parsed), f"{raw_output}\n\n--- repaired ---\n{repaired_output}"

    def _build_prompt(self, parent: RawItem, chunks: list[RawItem]) -> str:
        chunk_notes = "\n\n".join(self._chunk_note(chunk) for chunk in chunks)
        return self._prompt("book_brief.md").replace("{{title}}", parent.title).replace("{{chunks}}", chunk_notes)

    def _chunk_note(self, chunk: RawItem) -> str:
        metadata = chunk.metadata_json or {}
        page_start = metadata.get("page_start")
        page_end = metadata.get("page_end")
        page_label = f"pages {page_start}-{page_end}" if page_start and page_end and page_start != page_end else f"page {page_start}" if page_start else "pages unknown"
        memories = self._chunk_memories(chunk)
        summaries = "\n".join(f"- {memory.summary}" for memory in memories)
        tags = sorted({tag.name for memory in memories for tag in memory.tags})
        tag_line = f"\nTags: {', '.join(tags)}" if tags else ""
        return f"Chunk {metadata.get('chunk_index', '?')} ({page_label})\n{summaries}{tag_line}"

    def _document_chunks(self, parent_raw_item_id: str) -> list[RawItem]:
        chunks = self.db.scalars(select(RawItem).where(RawItem.source_type == "pdf_chunk").order_by(RawItem.created_at)).all()
        return [chunk for chunk in chunks if (chunk.metadata_json or {}).get("parent_raw_item_id") == parent_raw_item_id]

    def _chunk_memories(self, chunk: RawItem) -> list[Memory]:
        return list(
            self.db.scalars(
                select(Memory)
                .where(Memory.raw_item_id == chunk.id)
                .options(selectinload(Memory.tags), selectinload(Memory.tasks), selectinload(Memory.ideas), selectinload(Memory.decisions), selectinload(Memory.open_questions))
            ).all()
        )

    def _require_completed_chunks(self, parent_raw_item_id: str, chunks: list[RawItem] | None = None) -> None:
        chunks = chunks if chunks is not None else self._document_chunks(parent_raw_item_id)
        if not chunks:
            raise ValueError("No document chunks found for this item")
        incomplete = [chunk for chunk in chunks if chunk.status != "processed" or not self._chunk_memories(chunk)]
        if incomplete:
            raise ValueError(f"Book Brief requires all chunks to finish first. {len(incomplete)} chunks are incomplete.")

    def _existing_book_brief(self, parent_raw_item_id: str) -> Memory | None:
        memories = self.db.scalars(select(Memory).where(Memory.raw_item_id == parent_raw_item_id)).all()
        for memory in memories:
            if isinstance(memory.validated_json, dict) and memory.validated_json.get("source") == "book_brief":
                return memory
        return None

    def _tag_result_as_book_brief(self, result: ExtractionResult) -> ExtractionResult:
        tags = list(dict.fromkeys(["Book Brief", *result.tags]))
        return result.model_copy(update={"memory_type": "resource", "tags": tags})

    def _prompt(self, filename: str) -> str:
        return (self.settings.prompt_dir / filename).read_text(encoding="utf-8")


async def process_book_brief_run(run_id: str) -> None:
    db = SessionLocal()
    try:
        await BookBriefService(db).process_run(run_id)
    except Exception:
        return
    finally:
        db.close()
