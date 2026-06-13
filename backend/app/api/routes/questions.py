from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import OpenQuestion

router = APIRouter(prefix="/open-questions", tags=["open-questions"])


class QuestionPatch(BaseModel):
    question: str | None = None
    status: str | None = None


def question_dict(question: OpenQuestion) -> dict:
    return {
        "id": question.id,
        "memory_id": question.memory_id,
        "project_id": question.project_id,
        "question": question.question,
        "status": question.status,
        "source_raw_item_id": question.source_raw_item_id,
    }


@router.get("")
def list_questions(db: Session = Depends(get_db)) -> list[dict]:
    return [question_dict(question) for question in db.scalars(select(OpenQuestion).order_by(OpenQuestion.created_at.desc())).all()]


@router.patch("/{question_id}")
def patch_question(question_id: str, payload: QuestionPatch, db: Session = Depends(get_db)) -> dict:
    question = db.get(OpenQuestion, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Open question not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(question, field, value)
    db.commit()
    db.refresh(question)
    return question_dict(question)

