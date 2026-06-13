from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.models import Memory, RawItem
from app.schemas.raw_item import ManualItemCreate, RawItemOut
from app.services.extraction_service import ExtractionService

router = APIRouter(prefix="/items", tags=["items"])


@router.post("/manual", response_model=RawItemOut)
def create_manual_item(payload: ManualItemCreate, db: Session = Depends(get_db)) -> RawItem:
    title = payload.title or payload.body_text.strip().splitlines()[0][:80] or "Untitled note"
    item = RawItem(source_type="manual", title=title, body_text=payload.body_text)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.post("/upload", response_model=RawItemOut)
async def upload_item(file: UploadFile = File(...), db: Session = Depends(get_db)) -> RawItem:
    content = await file.read()
    try:
        body_text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="Only UTF-8 text uploads are supported in the MVP") from exc
    item = RawItem(
        source_type="upload",
        title=file.filename or "Uploaded text",
        body_text=body_text,
        content_type=file.content_type or "text/plain",
        source_uri=file.filename,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("", response_model=list[RawItemOut])
def list_items(db: Session = Depends(get_db)) -> list[RawItem]:
    return list(db.scalars(select(RawItem).order_by(RawItem.created_at.desc())).all())


@router.get("/{item_id}")
def get_item(item_id: str, db: Session = Depends(get_db)) -> dict:
    item = db.get(RawItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    memories = db.scalars(
        select(Memory)
        .where(Memory.raw_item_id == item_id)
        .options(selectinload(Memory.tags), selectinload(Memory.tasks), selectinload(Memory.ideas), selectinload(Memory.open_questions))
    ).all()
    return {
        "item": RawItemOut.model_validate(item).model_dump(mode="json"),
        "memories": [
            {
                "id": memory.id,
                "raw_item_id": memory.raw_item_id,
                "memory_type": memory.memory_type,
                "summary": memory.summary,
                "confidence": memory.confidence,
                "tags": [tag.name for tag in memory.tags],
                "tasks": [
                    {
                        "id": task.id,
                        "title": task.title,
                        "description": task.description,
                        "priority": task.priority,
                        "status": task.status,
                        "due_date": task.due_date.isoformat() if task.due_date else None,
                        "source_raw_item_id": task.source_raw_item_id,
                    }
                    for task in memory.tasks
                ],
                "ideas": [{"id": idea.id, "body": idea.body, "source_raw_item_id": idea.source_raw_item_id} for idea in memory.ideas],
                "open_questions": [
                    {
                        "id": question.id,
                        "question": question.question,
                        "status": question.status,
                        "source_raw_item_id": question.source_raw_item_id,
                    }
                    for question in memory.open_questions
                ],
                "created_at": memory.created_at.isoformat(),
            }
            for memory in memories
        ],
    }


@router.post("/{item_id}/process")
async def process_item(item_id: str, db: Session = Depends(get_db)) -> dict:
    item = db.get(RawItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    service = ExtractionService(db)
    try:
        memory = await service.process_item(item)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"memory_id": memory.id, "status": item.status}

