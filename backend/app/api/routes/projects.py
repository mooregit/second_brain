from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Decision, Idea, OpenQuestion, Project, Task
from app.services.project_brief_service import ProjectBriefService

router = APIRouter(prefix="/projects", tags=["projects"])


class ProjectPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    description: str | None = None


@router.get("")
def list_projects(db: Session = Depends(get_db)) -> list[dict]:
    return [
        {"id": project.id, "name": project.name, "description": project.description, "created_at": project.created_at.isoformat()}
        for project in db.scalars(select(Project).order_by(Project.name)).all()
    ]


@router.get("/{project_id}")
def get_project(project_id: str, db: Session = Depends(get_db)) -> dict:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"id": project.id, "name": project.name, "description": project.description, "created_at": project.created_at.isoformat()}


@router.get("/{project_id}/brief")
def get_project_brief(project_id: str, db: Session = Depends(get_db)) -> dict:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectBriefService(db).build(project)


@router.patch("/{project_id}")
def patch_project(project_id: str, payload: ProjectPatch, db: Session = Depends(get_db)) -> dict:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if payload.name is not None:
        normalized_name = payload.name.strip()
        if not normalized_name:
            raise HTTPException(status_code=422, detail="Project name is required")
        existing = db.scalar(select(Project).where(Project.name == normalized_name, Project.id != project_id))
        if existing:
            raise HTTPException(status_code=409, detail="Project name already exists")
        project.name = normalized_name
    if payload.description is not None:
        project.description = payload.description
    db.commit()
    db.refresh(project)
    return {"id": project.id, "name": project.name, "description": project.description, "created_at": project.created_at.isoformat()}


@router.delete("/{project_id}")
def delete_project(project_id: str, db: Session = Depends(get_db)) -> dict:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    for task in db.scalars(select(Task).where(Task.project_id == project_id)).all():
        task.project_id = None
    for idea in db.scalars(select(Idea).where(Idea.project_id == project_id)).all():
        idea.project_id = None
    for decision in db.scalars(select(Decision).where(Decision.project_id == project_id)).all():
        decision.project_id = None
    for question in db.scalars(select(OpenQuestion).where(OpenQuestion.project_id == project_id)).all():
        question.project_id = None

    db.delete(project)
    db.commit()
    return {"status": "deleted", "id": project_id}
