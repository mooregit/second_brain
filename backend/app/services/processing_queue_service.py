from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models import ProcessingRun, RawItem
from app.services.extraction_service import ExtractionService
from app.services.settings_service import SettingsService


ACTIVE_STATUSES = {"pending", "processing"}


class ProcessingQueueService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = SettingsService(db)

    def enqueue_item(self, raw_item_id: str, force: bool = False) -> ProcessingRun:
        item = self.db.get(RawItem, raw_item_id)
        if not item:
            raise ValueError("Item not found")

        if not force:
            active_run = self.db.scalar(
                select(ProcessingRun)
                .where(ProcessingRun.raw_item_id == raw_item_id, ProcessingRun.status.in_(ACTIVE_STATUSES))
                .order_by(ProcessingRun.started_at.desc())
            )
            if active_run:
                return active_run

        run = ProcessingRun(
            raw_item_id=item.id,
            status="pending",
            model=self.settings.get_ollama_extraction_model(),
            prompt_version="v1",
        )
        item.status = "pending"
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    async def process_run(self, run_id: str) -> ProcessingRun | None:
        run = self.db.get(ProcessingRun, run_id)
        if not run or run.status != "pending":
            return run

        item = self.db.get(RawItem, run.raw_item_id)
        if not item:
            run.status = "failed"
            run.finished_at = datetime.utcnow()
            run.error = "Raw item no longer exists."
            self.db.commit()
            return run

        try:
            await ExtractionService(self.db).process_item(item, run=run)
        except Exception as exc:
            self.db.refresh(run)
            item = self.db.get(RawItem, run.raw_item_id)
            if run.status not in {"failed", "succeeded"}:
                run.status = "failed"
                run.finished_at = datetime.utcnow()
                run.error = str(exc)
            if item and item.status == "processing":
                item.status = "failed"
            self.db.commit()
        return run

    async def process_pending(self, limit: int = 1) -> list[ProcessingRun]:
        self.requeue_stale_processing()
        runs = self.db.scalars(
            select(ProcessingRun).where(ProcessingRun.status == "pending").order_by(ProcessingRun.started_at).limit(limit)
        ).all()
        processed: list[ProcessingRun] = []
        for run in runs:
            result = await self.process_run(run.id)
            if result:
                processed.append(result)
        return processed

    def requeue_stale_processing(self) -> list[ProcessingRun]:
        cutoff = datetime.utcnow() - timedelta(minutes=get_settings().processing_stale_minutes)
        runs = self.db.scalars(
            select(ProcessingRun).where(ProcessingRun.status == "processing", ProcessingRun.started_at < cutoff)
        ).all()
        for run in runs:
            run.status = "pending"
            run.error = "Requeued after stale processing timeout."
            item = self.db.get(RawItem, run.raw_item_id)
            if item and item.status == "processing":
                item.status = "pending"
        if runs:
            self.db.commit()
        return runs

    def cancel_run(self, run_id: str) -> ProcessingRun:
        run = self.db.get(ProcessingRun, run_id)
        if not run:
            raise ValueError("Processing run not found")
        if run.status == "processing":
            raise RuntimeError("Processing has already started and cannot be canceled.")
        if run.status == "pending":
            run.status = "canceled"
            run.finished_at = datetime.utcnow()
            item = self.db.get(RawItem, run.raw_item_id)
            if item and item.status == "pending":
                item.status = "new"
            self.db.commit()
            self.db.refresh(run)
        return run

    def retry_run(self, run_id: str) -> ProcessingRun:
        run = self.db.get(ProcessingRun, run_id)
        if not run:
            raise ValueError("Processing run not found")
        return self.enqueue_item(run.raw_item_id, force=True)


async def process_queued_run(run_id: str) -> None:
    db = SessionLocal()
    try:
        await ProcessingQueueService(db).process_run(run_id)
    finally:
        db.close()
