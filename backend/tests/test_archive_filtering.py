import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.models import Embedding, Idea, Memory, OpenQuestion, RawItem, Task
from app.services.graph_service import GraphService
from app.services.retrieval_service import RetrievalService


@pytest.fixture
def db_session(tmp_path) -> Session:
    engine = create_engine(f"sqlite:///{tmp_path}/test.db", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine)


def test_retrieval_hydrate_skips_archived_child_records(db_session: Session) -> None:
    memory, raw_item = _memory(db_session)
    task = Task(memory_id=memory.id, title="Archived task", status="archived", source_raw_item_id=raw_item.id)
    idea = Idea(memory_id=memory.id, body="Archived idea", status="archived", source_raw_item_id=raw_item.id)
    question = OpenQuestion(memory_id=memory.id, question="Archived question?", status="archived", source_raw_item_id=raw_item.id)
    db_session.add_all([task, idea, question])
    db_session.commit()

    service = RetrievalService(db_session)
    assert service._hydrate(0.9, Embedding(owner_type="task", owner_id=task.id, model="test", vector_json=[1], text_hash="task")) is None
    assert service._hydrate(0.9, Embedding(owner_type="idea", owner_id=idea.id, model="test", vector_json=[1], text_hash="idea")) is None
    assert service._hydrate(
        0.9,
        Embedding(owner_type="open_question", owner_id=question.id, model="test", vector_json=[1], text_hash="question"),
    ) is None


def test_graph_hides_archived_records_by_default(db_session: Session) -> None:
    memory, raw_item = _memory(db_session)
    db_session.add_all(
        [
            Task(memory_id=memory.id, title="Active task", status="open", source_raw_item_id=raw_item.id),
            Task(memory_id=memory.id, title="Archived task", status="archived", source_raw_item_id=raw_item.id),
            Idea(memory_id=memory.id, body="Active idea", status="active", source_raw_item_id=raw_item.id),
            Idea(memory_id=memory.id, body="Archived idea", status="archived", source_raw_item_id=raw_item.id),
            OpenQuestion(memory_id=memory.id, question="Active question?", status="open", source_raw_item_id=raw_item.id),
            OpenQuestion(memory_id=memory.id, question="Archived question?", status="archived", source_raw_item_id=raw_item.id),
        ]
    )
    db_session.commit()

    graph = GraphService(db_session).build()
    labels = {node.label for node in graph.nodes}
    assert "Active task" in labels
    assert "Active idea" in labels
    assert "Active question?" in labels
    assert "Archived task" not in labels
    assert "Archived idea" not in labels
    assert "Archived question?" not in labels

    graph_with_archived = GraphService(db_session).build(show_archived=True)
    archived_labels = {node.label for node in graph_with_archived.nodes}
    assert "Archived task" in archived_labels
    assert "Archived idea" in archived_labels
    assert "Archived question?" in archived_labels


def test_graph_links_derived_records_to_their_source_raw_item(db_session: Session) -> None:
    memory, raw_item = _memory(db_session)
    task = Task(memory_id=memory.id, title="Website needs work", status="open", source_raw_item_id=raw_item.id)
    idea = Idea(memory_id=memory.id, body="https://saharamediterraneancuisine.shop/", status="active", source_raw_item_id=raw_item.id)
    db_session.add_all([task, idea])
    db_session.commit()

    graph = GraphService(db_session).build()
    source_node_id = f"source:{raw_item.id}"
    edge_pairs = {(edge.source, edge.target, edge.relationship_type) for edge in graph.edges}

    assert any(node.id == source_node_id and node.label == "Source" for node in graph.nodes)
    assert (source_node_id, f"task:{task.id}", "from_source") in edge_pairs
    assert (source_node_id, f"idea:{idea.id}", "from_source") in edge_pairs


def _memory(db_session: Session) -> tuple[Memory, RawItem]:
    raw_item = RawItem(source_type="manual", title="Source", body_text="Body", status="processed")
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
    db_session.add(memory)
    db_session.commit()
    return memory, raw_item
