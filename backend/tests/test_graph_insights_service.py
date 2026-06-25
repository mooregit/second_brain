from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.models import Memory, OpenQuestion, Project, RawItem, Relationship, Tag, Task
from app.api.routes.graph import normalize_relationships
from app.services.graph_insights_service import GraphInsightsService


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


def test_graph_insights_surface_cleanup_and_project_risks(db_session: Session) -> None:
    memory, raw_item = _memory(db_session)
    tag = Tag(name="BetRight")
    duplicate_tag = Tag(name="BetRight project")
    project = Project(name="BetRight App")
    db_session.add_all([tag, duplicate_tag, project])
    db_session.flush()
    memory.tags.extend([tag, duplicate_tag])
    db_session.add_all(
        [
            Task(memory_id=memory.id, title="Unassigned task", status="open", source_raw_item_id=raw_item.id),
            OpenQuestion(
                memory_id=memory.id,
                project_id=project.id,
                question="Should this affect projections?",
                status="open",
                source_raw_item_id=raw_item.id,
            ),
            Relationship(
                memory_id=memory.id,
                source_label="injury classification",
                target_label="player prop projections",
                relationship_type="related to",
                source_node_type="entity",
                target_node_type="entity",
                source_raw_item_id=raw_item.id,
            ),
        ]
    )
    db_session.commit()

    insights = GraphInsightsService(db_session).build()

    duplicate_labels = {label for candidate in insights.duplicate_candidates for label in candidate.labels}
    assert {"BetRight", "BetRight project"}.issubset(duplicate_labels)
    assert [(item.original_type, item.normalized_type, item.count) for item in insights.relationship_normalizations] == [("related to", "related_to", 1)]
    assert [(item.type, item.label, item.memory_id, item.source_title) for item in insights.unassigned_work_items] == [
        ("task", "Unassigned task", memory.id, "Source")
    ]
    betright_summary = next(summary for summary in insights.project_summaries if summary.project_id == project.id)
    assert betright_summary.open_questions == 1
    assert betright_summary.decisions == 0
    assert "questions_without_decisions" in betright_summary.risk_flags

    result = normalize_relationships(db_session)
    assert result == {"status": "normalized", "updated": 1}
    normalized = GraphInsightsService(db_session).build()
    assert normalized.relationship_normalizations == []


def test_graph_insights_hide_archived_unassigned_items_by_default(db_session: Session) -> None:
    memory, raw_item = _memory(db_session)
    db_session.add(Task(memory_id=memory.id, title="Archived task", status="archived", source_raw_item_id=raw_item.id))
    db_session.commit()

    hidden = GraphInsightsService(db_session).build()
    visible = GraphInsightsService(db_session).build(show_archived=True)

    assert hidden.unassigned_work_items == []
    assert [item.label for item in visible.unassigned_work_items] == ["Archived task"]


def _memory(db_session: Session) -> tuple[Memory, RawItem]:
    raw_item = RawItem(source_type="manual", title="Source", body_text="Source note", status="processed")
    db_session.add(raw_item)
    db_session.flush()
    memory = Memory(
        raw_item_id=raw_item.id,
        memory_type="note",
        summary="Summary",
        confidence=0.9,
        validated_json={},
        raw_llm_output="{}",
    )
    db_session.add(memory)
    db_session.flush()
    return memory, raw_item
