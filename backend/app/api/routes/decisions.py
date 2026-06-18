import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Decision, Memory, Project
from app.services.embedding_service import EmbeddingService

router = APIRouter(prefix="/decisions", tags=["decisions"])
logger = logging.getLogger(__name__)


class DecisionCreate(BaseModel):
    memory_id: str
    title: str = Field(min_length=1)
    rationale: str | None = None
    confidence: float = Field(default=0.0, ge=0, le=1)
    project_id: str | None = None


class DecisionPatch(BaseModel):
    title: str | None = None
    rationale: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    project_id: str | None = None


def decision_dict(decision: Decision) -> dict:
    return {
        "id": decision.id,
        "memory_id": decision.memory_id,
        "project_id": decision.project_id,
        "title": decision.title,
        "rationale": decision.rationale,
        "confidence": decision.confidence,
        "source_raw_item_id": decision.source_raw_item_id,
    }


@router.get("")
def list_decisions(db: Session = Depends(get_db)) -> list[dict]:
    return [decision_dict(decision) for decision in db.scalars(select(Decision).order_by(Decision.created_at.desc())).all()]


@router.post("")
async def create_decision(payload: DecisionCreate, db: Session = Depends(get_db)) -> dict:
    memory = db.get(Memory, payload.memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=422, detail="Decision title is required")
    decision = Decision(
        memory_id=memory.id,
        project_id=payload.project_id or _project_id_from_memory(memory, db),
        title=title,
        rationale=payload.rationale,
        confidence=payload.confidence,
        source_raw_item_id=memory.raw_item_id,
    )
    db.add(decision)
    db.commit()
    db.refresh(decision)
    await _embed_decision(decision, db)
    return decision_dict(decision)


@router.patch("/{decision_id}")
async def patch_decision(decision_id: str, payload: DecisionPatch, db: Session = Depends(get_db)) -> dict:
    decision = db.get(Decision, decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(decision, field, value)
    db.commit()
    db.refresh(decision)
    await _embed_decision(decision, db)
    return decision_dict(decision)


def _project_id_from_memory(memory: Memory, db: Session) -> str | None:
    projects = memory.validated_json.get("projects") if isinstance(memory.validated_json, dict) else None
    if not projects:
        return None
    project_name = str(projects[0]).strip()
    if not project_name:
        return None
    project = db.scalar(select(Project).where(Project.name == project_name))
    return project.id if project else None


async def _embed_decision(decision: Decision, db: Session) -> None:
    try:
        await EmbeddingService(db).embed_owner("decision", decision.id, f"{decision.title}\n{decision.rationale or ''}")
    except Exception as exc:
        logger.warning("Decision embedding refresh failed for %s: %s", decision.id, exc)
