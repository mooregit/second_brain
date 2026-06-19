import asyncio

from app.core.database import SessionLocal
from app.services.gmail_poller import GmailPoller
from app.services.processing_queue_service import ProcessingQueueService


def run_once() -> dict:
    async def _run() -> dict:
        gmail_result = await GmailPoller(SessionLocal).poll_once()
        db = SessionLocal()
        try:
            processed_runs = await ProcessingQueueService(db).process_pending(limit=3)
            processed_run_ids = [run.id for run in processed_runs]
        finally:
            db.close()
        return {
            "gmail": gmail_result,
            "processed_queue_count": len(processed_runs),
            "processed_run_ids": processed_run_ids,
        }

    return asyncio.run(_run())
