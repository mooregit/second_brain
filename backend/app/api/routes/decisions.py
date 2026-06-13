from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Decision

router = APIRouter(prefix="/decisions", tags=["decisions"])


@router.get("")
def list_decisions(db: Session = Depends(get_db)) -> list[dict]:
    return [
        {
            "id": decision.id,
            "memory_id": decision.memory_id,
            "project_id": decision.project_id,
            "title": decision.title,
            "rationale": decision.rationale,
            "confidence": decision.confidence,
            "source_raw_item_id": decision.source_raw_item_id,
        }
        for decision in db.scalars(select(Decision).order_by(Decision.created_at.desc())).all()
    ]

