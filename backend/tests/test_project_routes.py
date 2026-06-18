from collections.abc import Generator

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.api.routes.projects import ProjectPatch, delete_project, patch_project
from app.core.database import Base
from app.models import Decision, Idea, Memory, OpenQuestion, Project, RawItem, Task


@pytest.fixture
def db_session(tmp_path, monkeypatch: pytest.MonkeyPatch) -> Generator[Session, None, None]:
    engine = create_engine(f"sqlite:///{tmp_path}/test.db", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine)


def test_delete_project_detaches_related_records(db_session: Session) -> None:
    raw_item = RawItem(source_type="manual", title="Source", body_text="Body")
    db_session.add(raw_item)
    db_session.flush()
    memory = Memory(
        raw_item_id=raw_item.id,
        memory_type="note",
        summary="Summary",
        confidence=1.0,
        validated_json={},
        raw_llm_output="{}",
    )
    project = Project(name="https://saharamediterraneancuisine.shop/")
    db_session.add_all([memory, project])
    db_session.flush()
    db_session.add_all(
        [
            Task(memory_id=memory.id, project_id=project.id, title="Task", source_raw_item_id=raw_item.id),
            Idea(memory_id=memory.id, project_id=project.id, body="Idea", source_raw_item_id=raw_item.id),
            OpenQuestion(memory_id=memory.id, project_id=project.id, question="Question?", source_raw_item_id=raw_item.id),
            Decision(memory_id=memory.id, project_id=project.id, title="Decision", source_raw_item_id=raw_item.id),
        ]
    )
    db_session.commit()

    result = delete_project(project.id, db_session)

    assert result == {"status": "deleted", "id": project.id}
    assert db_session.get(Project, project.id) is None
    assert db_session.scalar(select(Task).where(Task.project_id.is_(None), Task.title == "Task")) is not None
    assert db_session.scalar(select(Idea).where(Idea.project_id.is_(None), Idea.body == "Idea")) is not None
    assert db_session.scalar(select(OpenQuestion).where(OpenQuestion.project_id.is_(None), OpenQuestion.question == "Question?")) is not None
    assert db_session.scalar(select(Decision).where(Decision.project_id.is_(None), Decision.title == "Decision")) is not None


def test_patch_project_renames_project(db_session: Session) -> None:
    project = Project(name="company workflows")
    db_session.add(project)
    db_session.commit()

    result = patch_project(project.id, ProjectPatch(name="Workflow Imagination"), db_session)

    assert result["name"] == "Workflow Imagination"
    assert db_session.get(Project, project.id).name == "Workflow Imagination"
