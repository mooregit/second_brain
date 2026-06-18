import asyncio
from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.routes.ideas import IdeaCreate, IdeaPatch, create_idea, patch_idea
from app.api.routes.memories import delete_memory
from app.api.routes.questions import QuestionCreate, QuestionPatch, create_question, patch_question
from app.api.routes.tasks import TaskCreate, TaskPatch, create_task, patch_task
from app.core.database import Base
from app.models import Embedding, Idea, Memory, RawItem, Task
from app.services.embedding_service import EmbeddingService


@pytest.fixture
def db_session(tmp_path, monkeypatch: pytest.MonkeyPatch) -> Generator[Session, None, None]:
    engine = create_engine(f"sqlite:///{tmp_path}/test.db", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(engine)

    async def fake_embed_owner(self: EmbeddingService, owner_type: str, owner_id: str, text: str) -> None:
        return None

    monkeypatch.setattr(EmbeddingService, "embed_owner", fake_embed_owner)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine)


def test_create_and_patch_review_children_preserves_source_traceability(db_session: Session) -> None:
    raw_item = RawItem(source_type="manual", title="Review source", body_text="Source note")
    db_session.add(raw_item)
    db_session.flush()
    memory = Memory(
        raw_item_id=raw_item.id,
        memory_type="note",
        summary="Review summary",
        confidence=0.5,
        validated_json={"projects": []},
        raw_llm_output="{}",
    )
    db_session.add(memory)
    db_session.commit()

    task = asyncio.run(
        create_task(
            TaskCreate(memory_id=memory.id, title="Manual task", description="Created during review", priority="medium"),
            db_session,
        )
    )
    assert task["memory_id"] == memory.id
    assert task["source_raw_item_id"] == raw_item.id

    patched_task = asyncio.run(patch_task(task["id"], TaskPatch(status="archived"), db_session))
    assert patched_task["status"] == "archived"

    idea = asyncio.run(create_idea(IdeaCreate(memory_id=memory.id, body="Manual idea"), db_session))
    assert idea["memory_id"] == memory.id
    assert idea["source_raw_item_id"] == raw_item.id
    assert idea["status"] == "active"

    patched_idea = asyncio.run(patch_idea(idea["id"], IdeaPatch(status="archived"), db_session))
    assert patched_idea["status"] == "archived"

    question = asyncio.run(create_question(QuestionCreate(memory_id=memory.id, question="Manual question?"), db_session))
    assert question["memory_id"] == memory.id
    assert question["source_raw_item_id"] == raw_item.id

    patched_question = asyncio.run(patch_question(question["id"], QuestionPatch(status="answered"), db_session))
    assert patched_question["status"] == "answered"


def test_delete_memory_removes_children_and_embeddings_but_keeps_source(db_session: Session) -> None:
    raw_item = RawItem(source_type="manual", title="Review source", body_text="Source note")
    db_session.add(raw_item)
    db_session.flush()
    memory = Memory(
        raw_item_id=raw_item.id,
        memory_type="note",
        summary="Review summary",
        confidence=0.5,
        validated_json={"projects": []},
        raw_llm_output="{}",
    )
    db_session.add(memory)
    db_session.flush()
    task = Task(memory_id=memory.id, title="Task", source_raw_item_id=raw_item.id)
    idea = Idea(memory_id=memory.id, body="Idea", source_raw_item_id=raw_item.id)
    db_session.add_all([task, idea])
    db_session.flush()
    db_session.add_all(
        [
            Embedding(owner_type="memory", owner_id=memory.id, model="test", vector_json=[1], text_hash="memory"),
            Embedding(owner_type="task", owner_id=task.id, model="test", vector_json=[1], text_hash="task"),
            Embedding(owner_type="idea", owner_id=idea.id, model="test", vector_json=[1], text_hash="idea"),
        ]
    )
    db_session.commit()

    result = delete_memory(memory.id, db_session)

    assert result == {"status": "deleted", "id": memory.id}
    assert db_session.get(RawItem, raw_item.id) is not None
    assert db_session.get(Memory, memory.id) is None
    assert db_session.get(Task, task.id) is None
    assert db_session.get(Idea, idea.id) is None
    assert db_session.query(Embedding).count() == 0
