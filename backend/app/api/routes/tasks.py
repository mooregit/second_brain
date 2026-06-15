import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Memory, Project, Task
from app.services.embedding_service import EmbeddingService

router = APIRouter(prefix="/tasks", tags=["tasks"])
logger = logging.getLogger(__name__)


class TaskCreate(BaseModel):
    memory_id: str
    title: str = Field(min_length=1)
    description: str | None = None
    priority: str | None = None
    status: str = "open"
    project_id: str | None = None


class TaskPatch(BaseModel):
    title: str | None = None
    description: str | None = None
    priority: str | None = None
    status: str | None = None


def task_dict(task: Task) -> dict:
    return {
        "id": task.id,
        "memory_id": task.memory_id,
        "project_id": task.project_id,
        "title": task.title,
        "description": task.description,
        "priority": task.priority,
        "status": task.status,
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "source_raw_item_id": task.source_raw_item_id,
    }


@router.get("")
def list_tasks(show_archived: bool = False, db: Session = Depends(get_db)) -> list[dict]:
    query = select(Task).order_by(Task.created_at.desc())
    if not show_archived:
        query = query.where(Task.status != "archived")
    return [task_dict(task) for task in db.scalars(query).all()]


@router.post("")
async def create_task(payload: TaskCreate, db: Session = Depends(get_db)) -> dict:
    memory = db.get(Memory, payload.memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=422, detail="Task title is required")
    project_id = payload.project_id or _project_id_from_memory(memory, db)
    task = Task(
        memory_id=memory.id,
        project_id=project_id,
        title=title,
        description=payload.description,
        priority=payload.priority,
        status=payload.status,
        source_raw_item_id=memory.raw_item_id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    await _embed_task(task, db)
    return task_dict(task)


@router.patch("/{task_id}")
async def patch_task(task_id: str, payload: TaskPatch, db: Session = Depends(get_db)) -> dict:
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    await _embed_task(task, db)
    return task_dict(task)


def _project_id_from_memory(memory: Memory, db: Session) -> str | None:
    projects = memory.validated_json.get("projects") if isinstance(memory.validated_json, dict) else None
    if not projects:
        return None
    project_name = str(projects[0]).strip()
    if not project_name:
        return None
    project = db.scalar(select(Project).where(Project.name == project_name))
    return project.id if project else None


async def _embed_task(task: Task, db: Session) -> None:
    try:
        await EmbeddingService(db).embed_owner("task", task.id, f"{task.title}\n{task.description or ''}")
    except Exception as exc:
        logger.warning("Task embedding refresh failed for %s: %s", task.id, exc)
