import asyncio
import os

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


def run_forever() -> None:
    poll_seconds = float(os.environ.get("WORKER_POLL_SECONDS", "5"))
    queue_limit = int(os.environ.get("PROCESSING_QUEUE_LIMIT", "1"))

    async def _loop() -> None:
        while True:
            db = SessionLocal()
            try:
                queue = ProcessingQueueService(db)
                stale_runs = queue.requeue_stale_processing()
                if stale_runs:
                    print(f"Requeued {len(stale_runs)} stale runs: {[run.id for run in stale_runs]}", flush=True)
                processed_runs = await queue.process_pending(limit=queue_limit)
                if processed_runs:
                    print(f"Processed {len(processed_runs)} queued runs: {[run.id for run in processed_runs]}", flush=True)
            except Exception as exc:
                print(f"Worker loop error: {exc}", flush=True)
            finally:
                db.close()
            await asyncio.sleep(poll_seconds)

    asyncio.run(_loop())


if __name__ == "__main__":
    run_forever()
