import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import AskRun, Decision, Memory, OpenQuestion, RawItem, Task
from app.schemas.ask import AskRequest, AskResponse, AskSaveRequest, AskSaveResponse
from app.services.embedding_service import EmbeddingService
from app.services.ask_service import AskService

router = APIRouter(prefix="/ask", tags=["ask"])
logger = logging.getLogger(__name__)


@router.post("", response_model=AskResponse)
async def ask(payload: AskRequest, db: Session = Depends(get_db)) -> AskResponse:
    try:
        return await AskService(db).ask(payload.question)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/{ask_run_id}/save", response_model=AskSaveResponse)
async def save_ask_result(ask_run_id: str, payload: AskSaveRequest, db: Session = Depends(get_db)) -> AskSaveResponse:
    ask_run = db.get(AskRun, ask_run_id)
    if not ask_run:
        raise HTTPException(status_code=404, detail="Ask run not found")

    raw_item, memory = _get_or_create_ask_memory(ask_run, db)
    if payload.save_as == "task":
        title = (payload.title or payload.body or ask_run.question).strip()
        if not title:
            raise HTTPException(status_code=422, detail="Task title is required")
        task = Task(
            memory_id=memory.id,
            title=title,
            description=payload.body or ask_run.answer,
            status="open",
            source_raw_item_id=raw_item.id,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        await _embed_owner("task", task.id, f"{task.title}\n{task.description or ''}", db)
        return AskSaveResponse(raw_item_id=raw_item.id, memory_id=memory.id, entity_type="task", entity_id=task.id)

    if payload.save_as == "open_question":
        question = (payload.title or payload.body or ask_run.question).strip()
        if not question:
            raise HTTPException(status_code=422, detail="Open question is required")
        open_question = OpenQuestion(memory_id=memory.id, question=question, status="open", source_raw_item_id=raw_item.id)
        db.add(open_question)
        db.commit()
        db.refresh(open_question)
        await _embed_owner("open_question", open_question.id, open_question.question, db)
        return AskSaveResponse(raw_item_id=raw_item.id, memory_id=memory.id, entity_type="open_question", entity_id=open_question.id)

    title = (payload.title or ask_run.question).strip()
    if not title:
        raise HTTPException(status_code=422, detail="Decision title is required")
    decision = Decision(
        memory_id=memory.id,
        title=title,
        rationale=payload.rationale or payload.body or ask_run.answer,
        confidence=payload.confidence,
        source_raw_item_id=raw_item.id,
    )
    db.add(decision)
    db.commit()
    db.refresh(decision)
    await _embed_owner("decision", decision.id, f"{decision.title}\n{decision.rationale or ''}", db)
    return AskSaveResponse(raw_item_id=raw_item.id, memory_id=memory.id, entity_type="decision", entity_id=decision.id)


def _get_or_create_ask_memory(ask_run: AskRun, db: Session) -> tuple[RawItem, Memory]:
    if ask_run.saved_raw_item_id:
        raw_item = db.get(RawItem, ask_run.saved_raw_item_id)
        if raw_item and raw_item.memories:
            return raw_item, raw_item.memories[0]

    raw_item = RawItem(
        source_type="ask",
        title=f"Ask: {ask_run.question[:72]}",
        body_text=f"Question:\n{ask_run.question}\n\nAnswer:\n{ask_run.answer}",
        status="processed",
        metadata_json={"ask_run_id": ask_run.id, "sources": ask_run.sources_json},
    )
    db.add(raw_item)
    db.flush()
    memory = Memory(
        raw_item_id=raw_item.id,
        memory_type="note",
        summary=f"Ask result: {ask_run.question}",
        confidence=1.0,
        validated_json={"source": "ask", "ask_run_id": ask_run.id},
        raw_llm_output=ask_run.answer,
    )
    db.add(memory)
    ask_run.saved_raw_item_id = raw_item.id
    db.commit()
    db.refresh(raw_item)
    db.refresh(memory)
    return raw_item, memory


async def _embed_owner(owner_type: str, owner_id: str, text: str, db: Session) -> None:
    try:
        await EmbeddingService(db).embed_owner(owner_type, owner_id, text)
    except Exception as exc:
        logger.warning("Ask save embedding failed for %s %s: %s", owner_type, owner_id, exc)
