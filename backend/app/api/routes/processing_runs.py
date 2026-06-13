from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import ProcessingRun

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
        }
        for run in runs
    ]

