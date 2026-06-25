from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.models import Idea, Memory, OpenQuestion, Project, RawItem, Task
from app.services.project_brief_service import ProjectBriefService


@pytest.fixture
def db_session(tmp_path) -> Generator[Session, None, None]:
    engine = create_engine(f"sqlite:///{tmp_path}/test.db", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine)


def test_project_brief_summarizes_project_health_and_sources(db_session: Session) -> None:
    raw_item = RawItem(source_type="manual", title="BetRight note", body_text="Need injury classification", status="processed")
    workflow_item = RawItem(
        source_type="github",
        title="BetRight workflow failed: Tests",
        body_text="GitHub workflow run failed: Tests",
        source_uri="github:rmoore/BetRight:workflow_run:3001",
        metadata_json={
            "github": {
                "item_type": "workflow_run",
                "repository": "rmoore/BetRight",
                "name": "Tests",
                "conclusion": "failure",
                "head_branch": "main",
                "html_url": "https://github.com/rmoore/BetRight/actions/runs/3001",
            }
        },
    )
    db_session.add_all([raw_item, workflow_item])
    db_session.flush()
    memory = Memory(
        raw_item_id=raw_item.id,
        memory_type="task",
        summary="BetRight needs injury classification.",
        confidence=0.8,
        validated_json={},
        raw_llm_output="{}",
    )
    project = Project(name="BetRight")
    db_session.add_all([memory, project])
    db_session.flush()
    db_session.add_all(
        [
            Task(memory_id=memory.id, project_id=project.id, title="Add injury classification", priority="high", source_raw_item_id=raw_item.id),
            Idea(memory_id=memory.id, project_id=project.id, body="Use local model for classification", source_raw_item_id=raw_item.id),
            OpenQuestion(memory_id=memory.id, project_id=project.id, question="Should injuries affect projections?", source_raw_item_id=raw_item.id),
        ]
    )
    db_session.commit()

    brief = ProjectBriefService(db_session).build(project)

    assert brief["counts"]["open_tasks"] == 1
    assert brief["counts"]["open_questions"] == 1
    assert brief["counts"]["active_ideas"] == 1
    assert "github_actions_failures" in brief["risks"]
    assert "questions_without_decisions" in brief["risks"]
    assert "high_priority_open_tasks" in brief["risks"]
    assert brief["next_actions"][0] == "Investigate failing GitHub Actions workflow: Tests"
    assert brief["github_failures"] == [
        {
            "raw_item_id": workflow_item.id,
            "name": "Tests",
            "repository": "rmoore/BetRight",
            "conclusion": "failure",
            "branch": "main",
            "url": "https://github.com/rmoore/BetRight/actions/runs/3001",
            "source_title": "BetRight workflow failed: Tests",
        }
    ]
    assert brief["recent_sources"] == [
        {
            "raw_item_id": raw_item.id,
            "title": "BetRight note",
            "source_type": "manual",
            "created_at": raw_item.created_at.isoformat(),
        }
    ]
