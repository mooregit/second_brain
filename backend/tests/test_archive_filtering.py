import pytest
from sqlalchemy import select
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.api.routes.graph import (
    LabelDelete,
    LabelRename,
    ManualRelationshipCreate,
    TagRename,
    create_manual_relationship,
    deduplicate_graph,
    delete_label,
    delete_tag,
    rename_label,
    rename_tag,
)
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
    edge_origins = {edge.relationship_type: edge.origin for edge in graph.edges}

    assert any(node.id == source_node_id and node.label == "Source" for node in graph.nodes)
    assert any(node.id == f"task:{task.id}" and node.metadata["task_id"] == task.id for node in graph.nodes)
    assert any(node.id == f"idea:{idea.id}" and node.metadata["idea_id"] == idea.id for node in graph.nodes)
    assert (source_node_id, f"task:{task.id}", "from_source") in edge_pairs
    assert (source_node_id, f"idea:{idea.id}", "from_source") in edge_pairs
    assert edge_origins["from_source"] == "source"


def test_graph_collapses_pdf_chunk_sources_to_parent_document(db_session: Session) -> None:
    parent = RawItem(source_type="upload", title="40algorithmseveryprogrammershouldknow.pdf", body_text="PDF parent", status="chunked")
    db_session.add(parent)
    db_session.flush()
    chunk = RawItem(
        source_type="pdf_chunk",
        title="40algorithmseveryprogrammershouldknow.pdf pages 51-58",
        body_text="Chunk body",
        status="processed",
        metadata_json={"parent_raw_item_id": parent.id, "chunk_index": 7, "page_start": 51, "page_end": 58},
    )
    db_session.add(chunk)
    db_session.flush()
    memory = Memory(
        raw_item_id=chunk.id,
        memory_type="note",
        summary="Binary search and merge sort.",
        confidence=1.0,
        validated_json={},
        raw_llm_output="{}",
    )
    tag = Tag(name="algorithms")
    db_session.add_all([memory, tag])
    db_session.flush()
    memory.tags.append(tag)
    task = Task(memory_id=memory.id, title="Review binary search notes", status="open", source_raw_item_id=chunk.id)
    db_session.add(task)
    db_session.commit()

    graph = GraphService(db_session).build()
    parent_source_node_id = f"source:{parent.id}"
    chunk_source_node_id = f"source:{chunk.id}"
    task_node = next(node for node in graph.nodes if node.id == f"task:{task.id}")
    source_node = next(node for node in graph.nodes if node.id == parent_source_node_id)
    edge_pairs = {(edge.source, edge.target, edge.relationship_type) for edge in graph.edges}

    assert source_node.label == "40algorithmseveryprogrammershouldknow.pdf"
    assert source_node.metadata["raw_item_id"] == parent.id
    assert not any(node.id == chunk_source_node_id for node in graph.nodes)
    assert task_node.metadata["raw_item_id"] == chunk.id
    assert task_node.metadata["source_title"] == parent.title
    assert task_node.metadata["source_type"] == "upload"
    assert task_node.metadata["chunk_raw_item_id"] == chunk.id
    assert task_node.metadata["chunk_page_start"] == 51
    assert task_node.metadata["chunk_page_end"] == 58
    assert (parent_source_node_id, f"task:{task.id}", "from_source") in edge_pairs
    assert (parent_source_node_id, f"tag:{tag.id}", "tagged") in edge_pairs


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
    edge_origins = {edge.relationship_type: edge.origin for edge in graph.edges}

    assert len(matching_nodes) == 1
    assert matching_nodes[0].type == "project"
    assert not any(node.type == "source" and node.label == "Workflow Imagination" for node in graph.nodes)
    assert (f"project:{project.id}", f"task:{task.id}", "from_source") in edge_pairs
    assert not any(edge.source == edge.target for edge in graph.edges)
    assert edge_origins["has_task"] == "project"
    assert edge_origins["from_source"] == "source"


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


def test_graph_relationship_reuses_existing_work_item_node_by_label(db_session: Session) -> None:
    memory, raw_item = _memory(db_session)
    project = Project(name="Workflow Imagination")
    db_session.add(project)
    db_session.flush()
    idea = Idea(
        memory_id=memory.id,
        project_id=project.id,
        body="Workflow imagination involves visualizing multi-step processes",
        source_raw_item_id=raw_item.id,
    )
    relationship = Relationship(
        memory_id=memory.id,
        source_label="Workflow imagination involves visualizing multi-step processes",
        target_label="Workflow Imagination",
        relationship_type="belongs_to",
        source_node_type="entity",
        target_node_type="project",
        source_raw_item_id=raw_item.id,
    )
    db_session.add_all([idea, relationship])
    db_session.commit()

    graph = GraphService(db_session).build()
    labels = [node.label for node in graph.nodes]
    edge_pairs = {(edge.source, edge.target, edge.relationship_type) for edge in graph.edges}

    assert labels.count("Workflow imagination involves visualizing multi-step processes") == 1
    assert ("idea:" + idea.id, "project:" + project.id, "belongs_to") in edge_pairs
    assert not any(node.id == "entity:workflow-imagination-involves-visualizing-multi-step-processes" for node in graph.nodes)


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


def test_graph_cleanup_renames_tag_and_merges_existing_tag(db_session: Session) -> None:
    memory, _ = _memory(db_session)
    old_tag = Tag(name="old workflow")
    existing_tag = Tag(name="workflow")
    db_session.add_all([old_tag, existing_tag])
    db_session.flush()
    memory.tags.extend([old_tag])
    db_session.commit()

    result = rename_tag(old_tag.id, TagRename(name="workflow"), db_session)
    db_session.refresh(memory)

    assert result["status"] == "merged"
    assert existing_tag in memory.tags
    assert old_tag not in memory.tags
    assert db_session.get(Tag, old_tag.id) is None


def test_graph_cleanup_deletes_tag(db_session: Session) -> None:
    memory, _ = _memory(db_session)
    tag = Tag(name="temporary")
    db_session.add(tag)
    db_session.flush()
    memory.tags.append(tag)
    db_session.commit()

    result = delete_tag(tag.id, db_session)
    db_session.refresh(memory)

    assert result == {"status": "deleted", "id": tag.id}
    assert tag not in memory.tags
    assert db_session.get(Tag, tag.id) is None


def test_graph_cleanup_renames_entity_label(db_session: Session) -> None:
    memory, raw_item = _memory(db_session)
    relationship = Relationship(
        memory_id=memory.id,
        source_label="old entity",
        target_label="target",
        relationship_type="mentions",
        source_node_type="entity",
        target_node_type="entity",
        source_raw_item_id=raw_item.id,
    )
    db_session.add(relationship)
    db_session.commit()

    result = rename_label(LabelRename(node_type="entity", old_label="old entity", new_label="new entity"), db_session)
    db_session.refresh(relationship)

    assert result["updated"] == 1
    assert relationship.source_label == "new entity"


def test_graph_cleanup_deletes_entity_label_relationships(db_session: Session) -> None:
    memory, raw_item = _memory(db_session)
    relationship = Relationship(
        memory_id=memory.id,
        source_label="remove me",
        target_label="target",
        relationship_type="mentions",
        source_node_type="entity",
        target_node_type="entity",
        source_raw_item_id=raw_item.id,
    )
    db_session.add(relationship)
    db_session.commit()

    result = delete_label(LabelDelete(node_type="entity", label="remove me"), db_session)

    assert result["deleted"] == 1
    assert db_session.get(Relationship, relationship.id) is None


def test_create_manual_relationship_adds_traceable_graph_edge(db_session: Session) -> None:
    result = create_manual_relationship(
        ManualRelationshipCreate(
            source_label="Orphan card",
            source_node_type="entity",
            target_label="Workflow Imagination",
            target_node_type="project",
            relationship_type="belongs_to",
        ),
        db_session,
    )

    relationship = db_session.get(Relationship, result["id"])
    graph = GraphService(db_session).build()
    edge_pairs = {(edge.source, edge.target, edge.relationship_type) for edge in graph.edges}

    assert relationship is not None
    assert relationship.source_label == "Orphan card"
    assert relationship.target_label == "Workflow Imagination"
    assert relationship.relationship_type == "belongs_to"
    assert any(node.label == "Orphan card" for node in graph.nodes)
    assert ("entity:orphan-card", "project:workflow-imagination", "belongs_to") in edge_pairs
    assert next(edge.origin for edge in graph.edges if edge.relationship_type == "belongs_to") == "manual"


def test_graph_deduplicate_merges_projects_tags_and_relationships(db_session: Session) -> None:
    memory, raw_item = _memory(db_session)
    canonical_project = Project(name="Workflow Imagination")
    duplicate_project = Project(name="workflow imagination project")
    canonical_tag = Tag(name="website")
    duplicate_tag = Tag(name=" Website ")
    db_session.add_all([canonical_project, duplicate_project, canonical_tag, duplicate_tag])
    db_session.flush()
    task = Task(memory_id=memory.id, project_id=duplicate_project.id, title="Task", source_raw_item_id=raw_item.id)
    memory.tags.extend([duplicate_tag])
    relationship = Relationship(
        memory_id=memory.id,
        source_label=" Workflow Imagination Project ",
        target_label="Task ",
        relationship_type="Related To",
        source_node_type="entity",
        target_node_type="task",
        source_raw_item_id=raw_item.id,
    )
    duplicate_relationship = Relationship(
        memory_id=memory.id,
        source_label="workflow imagination",
        target_label="Task",
        relationship_type="related_to",
        source_node_type="project",
        target_node_type="task",
        source_raw_item_id=raw_item.id,
    )
    db_session.add_all([task, relationship, duplicate_relationship])
    db_session.commit()

    result = deduplicate_graph(db_session)
    db_session.refresh(task)
    db_session.refresh(memory)

    assert result["status"] == "deduplicated"
    assert result["projects_merged"] == 1
    assert result["tags_merged"] == 1
    assert result["relationships_removed"] == 1
    assert result["relationship_node_types_updated"] == 1
    assert task.project_id == canonical_project.id
    assert canonical_tag in memory.tags
    assert duplicate_tag not in memory.tags
    assert db_session.get(Project, duplicate_project.id) is None
    assert db_session.get(Tag, duplicate_tag.id) is None
    remaining_relationships = db_session.scalars(select(Relationship)).all()
    assert len(remaining_relationships) == 1
    assert remaining_relationships[0].source_label == "Workflow Imagination"
    assert remaining_relationships[0].target_label == "Task"
    assert remaining_relationships[0].relationship_type == "related_to"


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
