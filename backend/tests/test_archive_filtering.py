import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.models import EmailMessage, Embedding, Idea, Memory, OpenQuestion, Project, RawItem, Relationship, Tag, Task
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
    assert any(node.id == f"task:{task.id}" and node.metadata["task_id"] == task.id for node in graph.nodes)
    assert any(node.id == f"idea:{idea.id}" and node.metadata["idea_id"] == idea.id for node in graph.nodes)
    assert (source_node_id, f"task:{task.id}", "from_source") in edge_pairs
    assert (source_node_id, f"idea:{idea.id}", "from_source") in edge_pairs


def test_graph_work_nodes_include_source_filter_metadata(db_session: Session) -> None:
    memory, raw_item = _memory(db_session)
    task = Task(memory_id=memory.id, title="Website needs work", status="open", source_raw_item_id=raw_item.id)
    db_session.add(task)
    db_session.commit()

    graph = GraphService(db_session).build()
    task_node = next(node for node in graph.nodes if node.id == f"task:{task.id}")

    assert task_node.metadata["source_type"] == raw_item.source_type
    assert task_node.metadata["source_created_at"].startswith(raw_item.created_at.date().isoformat())


def test_graph_hides_source_node_when_title_duplicates_derived_record(db_session: Session) -> None:
    raw_item = RawItem(source_type="gmail", title="Website needs work", body_text="https://saharamediterraneancuisine.shop/", status="processed")
    db_session.add(raw_item)
    db_session.flush()
    memory = Memory(
        raw_item_id=raw_item.id,
        memory_type="email",
        summary="Website needs work.",
        confidence=1.0,
        validated_json={},
        raw_llm_output="{}",
    )
    db_session.add(memory)
    db_session.flush()
    task = Task(memory_id=memory.id, title="Website needs work", status="open", source_raw_item_id=raw_item.id)
    db_session.add(task)
    db_session.commit()

    graph = GraphService(db_session).build()

    assert any(node.id == f"task:{task.id}" for node in graph.nodes)
    assert not any(node.id == f"source:{raw_item.id}" for node in graph.nodes)
    assert not any(edge.source == f"source:{raw_item.id}" or edge.target == f"source:{raw_item.id}" for edge in graph.edges)


def test_graph_hides_isolated_projects(db_session: Session) -> None:
    db_session.add(Project(name="https://saharamediterraneancuisine.shop/"))
    db_session.commit()

    graph = GraphService(db_session).build()

    assert "https://saharamediterraneancuisine.shop/" not in {node.label for node in graph.nodes}


def test_graph_shows_projects_with_active_records(db_session: Session) -> None:
    memory, raw_item = _memory(db_session)
    project = Project(name="Website needs work")
    db_session.add(project)
    db_session.flush()
    db_session.add(Task(memory_id=memory.id, project_id=project.id, title="Fix website", status="open", source_raw_item_id=raw_item.id))
    db_session.commit()

    graph = GraphService(db_session).build()

    assert "Website needs work" in {node.label for node in graph.nodes}


def test_graph_uses_project_node_when_source_title_matches_project(db_session: Session) -> None:
    raw_item = RawItem(source_type="gmail", title="Workflow Imagination", body_text="Body", status="processed")
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
    project = Project(name="Workflow Imagination")
    db_session.add_all([memory, project])
    db_session.flush()
    task = Task(memory_id=memory.id, project_id=project.id, title="Analyze workflows", status="open", source_raw_item_id=raw_item.id)
    db_session.add(task)
    db_session.commit()

    graph = GraphService(db_session).build()
    matching_nodes = [node for node in graph.nodes if node.label == "Workflow Imagination"]
    edge_pairs = {(edge.source, edge.target, edge.relationship_type) for edge in graph.edges}

    assert len(matching_nodes) == 1
    assert matching_nodes[0].type == "project"
    assert not any(node.type == "source" and node.label == "Workflow Imagination" for node in graph.nodes)
    assert (f"project:{project.id}", f"task:{task.id}", "from_source") in edge_pairs
    assert not any(edge.source == edge.target for edge in graph.edges)


def test_graph_links_relationship_nodes_to_their_source_raw_item(db_session: Session) -> None:
    memory, raw_item = _memory(db_session)
    relationship = Relationship(
        memory_id=memory.id,
        source_label="Website needs work",
        target_label="https://saharamediterraneancuisine.shop/",
        relationship_type="mentions",
        source_node_type="entity",
        target_node_type="entity",
        source_raw_item_id=raw_item.id,
    )
    db_session.add(relationship)
    db_session.commit()

    graph = GraphService(db_session).build()
    source_node_id = f"source:{raw_item.id}"
    url_node_id = "entity:https://saharamediterraneancuisine.shop/"
    edge_pairs = {(edge.source, edge.target, edge.relationship_type) for edge in graph.edges}

    assert any(node.id == source_node_id and node.label == "Source" for node in graph.nodes)
    assert any(node.id == url_node_id for node in graph.nodes)
    assert (source_node_id, "entity:website-needs-work", "from_source") in edge_pairs
    assert (source_node_id, url_node_id, "from_source") in edge_pairs
    assert ("entity:website-needs-work", url_node_id, "mentions") in edge_pairs


def test_graph_skips_orphan_relationship_nodes(db_session: Session) -> None:
    memory, _raw_item = _memory(db_session)
    db_session.add(
        Relationship(
            memory_id=memory.id,
            source_label="Website needs work",
            target_label="https://saharamediterraneancuisine.shop/",
            relationship_type="mentions",
            source_node_type="entity",
            target_node_type="entity",
            source_raw_item_id="missing-raw-item-id",
        )
    )
    db_session.commit()

    graph = GraphService(db_session).build()
    labels = {node.label for node in graph.nodes}

    assert "Website needs work" not in labels
    assert "https://saharamediterraneancuisine.shop/" not in labels


def test_graph_hides_gmail_sender_signature_tags_and_relationships(db_session: Session) -> None:
    raw_item = RawItem(
        source_type="gmail",
        title="Website needs work",
        body_text="https://saharamediterraneancuisine.shop/\n\nRussell G. Moore",
        status="processed",
    )
    db_session.add(raw_item)
    db_session.flush()
    db_session.add(
        EmailMessage(
            raw_item_id=raw_item.id,
            gmail_message_id="gmail-signature-graph",
            from_email="russell@example.com",
            subject="Website needs work",
        )
    )
    memory = Memory(
        raw_item_id=raw_item.id,
        memory_type="email",
        summary="Website needs work.",
        confidence=1.0,
        validated_json={},
        raw_llm_output="{}",
    )
    sender_tag = Tag(name="Russell G. Moore")
    useful_tag = Tag(name="website")
    db_session.add_all([memory, sender_tag, useful_tag])
    db_session.flush()
    memory.tags.extend([sender_tag, useful_tag])
    db_session.add(
        Relationship(
            memory_id=memory.id,
            source_label="Website needs work",
            target_label="Russell G. Moore",
            relationship_type="related_to",
            source_node_type="entity",
            target_node_type="person",
            source_raw_item_id=raw_item.id,
        )
    )
    db_session.commit()

    graph = GraphService(db_session).build()
    labels = {node.label for node in graph.nodes}

    assert "Russell G. Moore" not in labels
    assert "website" in labels


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
