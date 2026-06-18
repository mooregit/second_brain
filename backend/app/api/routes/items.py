from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.models import AskRun, EmailMessage, Embedding, FileAsset, MediaArtifact, Memory, ProcessingRun, RawItem
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


@router.delete("/{item_id}")
def delete_item(item_id: str, db: Session = Depends(get_db)) -> dict:
    item = db.scalars(
        select(RawItem)
        .where(RawItem.id == item_id)
        .options(selectinload(RawItem.memories), selectinload(RawItem.processing_runs))
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    memory_ids = [memory.id for memory in item.memories]
    child_owner_ids: list[tuple[str, str]] = [("memory", memory_id) for memory_id in memory_ids]
    for memory in item.memories:
        child_owner_ids.extend(("task", task.id) for task in memory.tasks)
        child_owner_ids.extend(("idea", idea.id) for idea in memory.ideas)
        child_owner_ids.extend(("decision", decision.id) for decision in memory.decisions)
        child_owner_ids.extend(("open_question", question.id) for question in memory.open_questions)

    for owner_type, owner_id in child_owner_ids:
        for embedding in db.scalars(select(Embedding).where(Embedding.owner_type == owner_type, Embedding.owner_id == owner_id)).all():
            db.delete(embedding)
    for email_message in db.scalars(select(EmailMessage).where(EmailMessage.raw_item_id == item_id)).all():
        db.delete(email_message)
    for media_artifact in db.scalars(select(MediaArtifact).where(MediaArtifact.raw_item_id == item_id)).all():
        db.delete(media_artifact)
    for file_asset in db.scalars(select(FileAsset).where(FileAsset.raw_item_id == item_id)).all():
        db.delete(file_asset)
    for ask_run in db.scalars(select(AskRun).where(AskRun.saved_raw_item_id == item_id)).all():
        ask_run.saved_raw_item_id = None

    db.delete(item)
    db.commit()
    return {"status": "deleted", "id": item_id}


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
    file_assets = db.scalars(select(FileAsset).where(FileAsset.raw_item_id == item_id).order_by(FileAsset.filename)).all()
    artifacts_by_file_asset: dict[str, list[MediaArtifact]] = {}
    for artifact in db.scalars(select(MediaArtifact).where(MediaArtifact.raw_item_id == item_id).order_by(MediaArtifact.created_at.desc())).all():
        artifacts_by_file_asset.setdefault(artifact.file_asset_id, []).append(artifact)
    return {
        "item": RawItemOut.model_validate(item).model_dump(mode="json"),
        "latest_processing_run": processing_run_dict(latest_run) if latest_run else None,
        "file_assets": [
            {
                "id": asset.id,
                "filename": asset.filename,
                "stored_path": asset.stored_path,
                "mime_type": asset.mime_type,
                "size_bytes": asset.size_bytes,
                "sha256": asset.sha256,
                "media_artifacts": [
                    {
                        "id": artifact.id,
                        "artifact_type": artifact.artifact_type,
                        "status": artifact.status,
                        "text_content": artifact.text_content,
                        "stored_path": artifact.stored_path,
                        "metadata_json": artifact.metadata_json,
                        "error": artifact.error,
                        "created_at": artifact.created_at.isoformat(),
                        "updated_at": artifact.updated_at.isoformat(),
                    }
                    for artifact in artifacts_by_file_asset.get(asset.id, [])
                ],
            }
            for asset in file_assets
        ],
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
