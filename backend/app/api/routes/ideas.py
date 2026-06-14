from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Idea

router = APIRouter(prefix="/ideas", tags=["ideas"])


class IdeaPatch(BaseModel):
    body: str | None = None


def idea_dict(idea: Idea) -> dict:
    return {
        "id": idea.id,
        "memory_id": idea.memory_id,
        "project_id": idea.project_id,
        "body": idea.body,
        "source_raw_item_id": idea.source_raw_item_id,
    }


@router.get("")
def list_ideas(db: Session = Depends(get_db)) -> list[dict]:
    return [idea_dict(idea) for idea in db.scalars(select(Idea).order_by(Idea.created_at.desc())).all()]


@router.patch("/{idea_id}")
def patch_idea(idea_id: str, payload: IdeaPatch, db: Session = Depends(get_db)) -> dict:
    idea = db.get(Idea, idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(idea, field, value)
    db.commit()
    db.refresh(idea)
    return idea_dict(idea)

