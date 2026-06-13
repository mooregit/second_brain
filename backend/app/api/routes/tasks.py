from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Task

router = APIRouter(prefix="/tasks", tags=["tasks"])


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
def list_tasks(db: Session = Depends(get_db)) -> list[dict]:
    return [task_dict(task) for task in db.scalars(select(Task).order_by(Task.created_at.desc())).all()]


@router.patch("/{task_id}")
def patch_task(task_id: str, payload: TaskPatch, db: Session = Depends(get_db)) -> dict:
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task_dict(task)

