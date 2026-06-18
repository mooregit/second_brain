import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Idea, Memory, Project
from app.services.embedding_service import EmbeddingService

router = APIRouter(prefix="/ideas", tags=["ideas"])
logger = logging.getLogger(__name__)


class IdeaCreate(BaseModel):
    memory_id: str
    body: str = Field(min_length=1)
    status: str = "active"
    project_id: str | None = None


class IdeaPatch(BaseModel):
    body: str | None = None
    status: str | None = None
    project_id: str | None = None


def idea_dict(idea: Idea) -> dict:
    return {
        "id": idea.id,
        "memory_id": idea.memory_id,
        "project_id": idea.project_id,
        "body": idea.body,
        "status": idea.status,
        "source_raw_item_id": idea.source_raw_item_id,
    }


@router.get("")
def list_ideas(db: Session = Depends(get_db)) -> list[dict]:
    return [idea_dict(idea) for idea in db.scalars(select(Idea).order_by(Idea.created_at.desc())).all()]


@router.post("")
async def create_idea(payload: IdeaCreate, db: Session = Depends(get_db)) -> dict:
    memory = db.get(Memory, payload.memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    body = payload.body.strip()
    if not body:
        raise HTTPException(status_code=422, detail="Idea body is required")
    idea = Idea(
        memory_id=memory.id,
        project_id=payload.project_id or _project_id_from_memory(memory, db),
        body=body,
        status=payload.status,
        source_raw_item_id=memory.raw_item_id,
    )
    db.add(idea)
    db.commit()
    db.refresh(idea)
    await _embed_idea(idea, db)
    return idea_dict(idea)


@router.patch("/{idea_id}")
async def patch_idea(idea_id: str, payload: IdeaPatch, db: Session = Depends(get_db)) -> dict:
    idea = db.get(Idea, idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(idea, field, value)
    db.commit()
    db.refresh(idea)
    await _embed_idea(idea, db)
    return idea_dict(idea)


def _project_id_from_memory(memory: Memory, db: Session) -> str | None:
    projects = memory.validated_json.get("projects") if isinstance(memory.validated_json, dict) else None
    if not projects:
        return None
    project_name = str(projects[0]).strip()
    if not project_name:
        return None
    project = db.scalar(select(Project).where(Project.name == project_name))
    return project.id if project else None


async def _embed_idea(idea: Idea, db: Session) -> None:
    try:
        await EmbeddingService(db).embed_owner("idea", idea.id, idea.body)
    except Exception as exc:
        logger.warning("Idea embedding refresh failed for %s: %s", idea.id, exc)
