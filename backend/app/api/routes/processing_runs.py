from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import ProcessingRun
from app.services.processing_queue_service import ProcessingQueueService, process_queued_run

router = APIRouter(prefix="/processing-runs", tags=["processing-runs"])


@router.get("")
def list_processing_runs(db: Session = Depends(get_db)) -> list[dict]:
    runs = db.scalars(select(ProcessingRun).order_by(ProcessingRun.started_at.desc())).all()
    return [
        {
            "id": run.id,
            "raw_item_id": run.raw_item_id,
            "status": run.status,
            "model": run.model,
            "started_at": run.started_at.isoformat(),
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "error": run.error,
            "raw_output": run.raw_output,
            "parsed_json": run.parsed_json,
        }
        for run in runs
    ]


@router.post("/{run_id}/cancel")
def cancel_processing_run(run_id: str, db: Session = Depends(get_db)) -> dict:
    try:
        run = ProcessingQueueService(db).cancel_run(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return processing_run_dict(run)


@router.post("/{run_id}/retry")
def retry_processing_run(run_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)) -> dict:
    try:
        run = ProcessingQueueService(db).retry_run(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    background_tasks.add_task(process_queued_run, run.id)
    return processing_run_dict(run)


def processing_run_dict(run: ProcessingRun) -> dict:
    return {
        "id": run.id,
        "raw_item_id": run.raw_item_id,
        "status": run.status,
        "model": run.model,
        "started_at": run.started_at.isoformat(),
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "error": run.error,
        "raw_output": run.raw_output,
        "parsed_json": run.parsed_json,
    }
