import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Embedding, Memory, OpenQuestion, Project
from app.schemas.ask import AskResponse
from app.services.ask_service import AskService
from app.services.embedding_service import EmbeddingService

router = APIRouter(prefix="/open-questions", tags=["open-questions"])
logger = logging.getLogger(__name__)


class QuestionCreate(BaseModel):
    memory_id: str
    question: str = Field(min_length=1)
    status: str = "open"
    project_id: str | None = None


class QuestionPatch(BaseModel):
    question: str | None = None
    status: str | None = None
    project_id: str | None = None
    answer_text: str | None = None
    answer_confidence: float | None = Field(default=None, ge=0, le=1)
    answer_sources_json: list[dict] | None = None


class QuestionAnswer(BaseModel):
    answer_text: str = Field(min_length=1)
    answer_confidence: float | None = Field(default=None, ge=0, le=1)
    answer_sources_json: list[dict] = Field(default_factory=list)


def question_dict(question: OpenQuestion) -> dict:
    return {
        "id": question.id,
        "memory_id": question.memory_id,
        "project_id": question.project_id,
        "question": question.question,
        "status": question.status,
        "answer_text": question.answer_text,
        "answer_confidence": question.answer_confidence,
        "answer_sources_json": question.answer_sources_json or [],
        "answered_at": question.answered_at.isoformat() if question.answered_at else None,
        "source_raw_item_id": question.source_raw_item_id,
    }


@router.get("")
def list_questions(show_archived: bool = False, db: Session = Depends(get_db)) -> list[dict]:
    query = select(OpenQuestion).order_by(OpenQuestion.created_at.desc())
    if not show_archived:
        query = query.where(OpenQuestion.status != "archived")
    return [question_dict(question) for question in db.scalars(query).all()]


@router.post("")
async def create_question(payload: QuestionCreate, db: Session = Depends(get_db)) -> dict:
    memory = db.get(Memory, payload.memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    question_text = payload.question.strip()
    if not question_text:
        raise HTTPException(status_code=422, detail="Question is required")
    question = OpenQuestion(
        memory_id=memory.id,
        project_id=payload.project_id or _project_id_from_memory(memory, db),
        question=question_text,
        status=payload.status,
        source_raw_item_id=memory.raw_item_id,
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    await _embed_question(question, db)
    return question_dict(question)


@router.patch("/{question_id}")
async def patch_question(question_id: str, payload: QuestionPatch, db: Session = Depends(get_db)) -> dict:
    question = db.get(OpenQuestion, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Open question not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(question, field, value)
    if payload.answer_text is not None and payload.answer_text.strip():
        question.status = "answered"
        question.answered_at = datetime.utcnow()
    db.commit()
    db.refresh(question)
    await _embed_question(question, db)
    return question_dict(question)


@router.post("/{question_id}/ask", response_model=AskResponse)
async def ask_open_question(question_id: str, db: Session = Depends(get_db)) -> AskResponse:
    question = db.get(OpenQuestion, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Open question not found")
    try:
        return await AskService(db).ask(question.question)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/{question_id}/answer")
async def answer_question(question_id: str, payload: QuestionAnswer, db: Session = Depends(get_db)) -> dict:
    question = db.get(OpenQuestion, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Open question not found")
    question.answer_text = payload.answer_text.strip()
    question.answer_confidence = payload.answer_confidence
    question.answer_sources_json = payload.answer_sources_json
    question.status = "answered"
    question.answered_at = datetime.utcnow()
    db.commit()
    db.refresh(question)
    await _embed_question(question, db)
    return question_dict(question)


@router.delete("/{question_id}")
def delete_question(question_id: str, db: Session = Depends(get_db)) -> dict:
    question = db.get(OpenQuestion, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Open question not found")
    for embedding in db.scalars(select(Embedding).where(Embedding.owner_type == "open_question", Embedding.owner_id == question_id)).all():
        db.delete(embedding)
    db.delete(question)
    db.commit()
    return {"status": "deleted", "id": question_id}


def _project_id_from_memory(memory: Memory, db: Session) -> str | None:
    projects = memory.validated_json.get("projects") if isinstance(memory.validated_json, dict) else None
    if not projects:
        return None
    project_name = str(projects[0]).strip()
    if not project_name:
        return None
    project = db.scalar(select(Project).where(Project.name == project_name))
    return project.id if project else None


async def _embed_question(question: OpenQuestion, db: Session) -> None:
    try:
        text = question.question if not question.answer_text else f"{question.question}\nAnswer: {question.answer_text}"
        await EmbeddingService(db).embed_owner("open_question", question.id, text)
    except Exception as exc:
        logger.warning("Open question embedding refresh failed for %s: %s", question.id, exc)
