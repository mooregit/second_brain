from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.models import Memory, ProcessingRun, RawItem
from app.schemas.raw_item import ManualItemCreate, RawItemOut
from app.services.extraction_service import ExtractionService
from app.services.file_service import FileService

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


@router.post("/scan-inbox")
def scan_inbox(db: Session = Depends(get_db)) -> dict:
    try:
        result = FileService(db).scan_inbox_folder()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "folder": result["folder"],
        "created_count": result["created_count"],
        "skipped_count": result["skipped_count"],
        "created_items": [RawItemOut.model_validate(item).model_dump(mode="json") for item in result["created_items"]],
        "skipped_files": result["skipped_files"],
    }


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
        .options(selectinload(Memory.tags), selectinload(Memory.tasks), selectinload(Memory.ideas), selectinload(Memory.decisions), selectinload(Memory.open_questions))
    ).all()
    latest_run = db.scalars(
        select(ProcessingRun).where(ProcessingRun.raw_item_id == item_id).order_by(ProcessingRun.started_at.desc())
    ).first()
    return {
        "item": RawItemOut.model_validate(item).model_dump(mode="json"),
        "latest_processing_run": processing_run_dict(latest_run) if latest_run else None,
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
                "ideas": [
                    {"id": idea.id, "body": idea.body, "status": idea.status, "source_raw_item_id": idea.source_raw_item_id}
                    for idea in memory.ideas
                ],
                "decisions": [
                    {
                        "id": decision.id,
                        "title": decision.title,
                        "rationale": decision.rationale,
                        "confidence": decision.confidence,
                        "source_raw_item_id": decision.source_raw_item_id,
                    }
                    for decision in memory.decisions
                ],
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


def processing_run_dict(run: ProcessingRun) -> dict:
    raw_output = run.raw_output or ""
    original_output, repaired_output = split_repair_output(raw_output)
    return {
        "id": run.id,
        "raw_item_id": run.raw_item_id,
        "status": run.status,
        "model": run.model,
        "prompt_version": run.prompt_version,
        "started_at": run.started_at.isoformat(),
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "error": run.error,
        "raw_output": raw_output,
        "original_output": original_output,
        "repaired_output": repaired_output,
        "parsed_json": run.parsed_json,
    }


def split_repair_output(raw_output: str) -> tuple[str, str | None]:
    marker = "\n\n--- repaired ---\n"
    if marker not in raw_output:
        return raw_output, None
    original, repaired = raw_output.split(marker, 1)
    return original, repaired
