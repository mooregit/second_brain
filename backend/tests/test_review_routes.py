import asyncio
from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.routes.decisions import DecisionCreate, create_decision, delete_decision
from app.api.routes.ideas import IdeaCreate, IdeaPatch, create_idea, delete_idea, patch_idea
from app.api.routes.memories import delete_memory
from app.api.routes.questions import QuestionAnswer, QuestionCreate, QuestionPatch, answer_question, create_question, delete_question, patch_question
from app.api.routes.tasks import TaskCreate, TaskPatch, create_task, delete_task, patch_task
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


def test_answer_question_saves_answer_metadata_and_traceability(db_session: Session) -> None:
    raw_item = RawItem(source_type="manual", title="Question source", body_text="Source note")
    db_session.add(raw_item)
    db_session.flush()
    memory = Memory(
        raw_item_id=raw_item.id,
        memory_type="note",
        summary="Question summary",
        confidence=0.5,
        validated_json={"projects": []},
        raw_llm_output="{}",
    )
    db_session.add(memory)
    db_session.commit()

    question = asyncio.run(create_question(QuestionCreate(memory_id=memory.id, question="What should happen next?"), db_session))
    answer = asyncio.run(
        answer_question(
            question["id"],
            QuestionAnswer(
                answer_text="Use the stored source to decide the next action.",
                answer_confidence=0.8,
                answer_sources_json=[{"raw_item_id": raw_item.id, "title": raw_item.title, "score": 0.91}],
            ),
            db_session,
        )
    )

    assert answer["status"] == "answered"
    assert answer["answer_text"] == "Use the stored source to decide the next action."
    assert answer["answer_confidence"] == 0.8
    assert answer["answer_sources_json"] == [{"raw_item_id": raw_item.id, "title": raw_item.title, "score": 0.91}]
    assert answer["answered_at"] is not None
    assert answer["memory_id"] == memory.id
    assert answer["source_raw_item_id"] == raw_item.id


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


def test_delete_review_children_removes_embeddings(db_session: Session) -> None:
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

    task = asyncio.run(create_task(TaskCreate(memory_id=memory.id, title="Task"), db_session))
    idea = asyncio.run(create_idea(IdeaCreate(memory_id=memory.id, body="Idea"), db_session))
    decision = asyncio.run(create_decision(DecisionCreate(memory_id=memory.id, title="Decision"), db_session))
    question = asyncio.run(create_question(QuestionCreate(memory_id=memory.id, question="Question?"), db_session))
    db_session.add_all(
        [
            Embedding(owner_type="task", owner_id=task["id"], model="test", vector_json=[1], text_hash="task"),
            Embedding(owner_type="idea", owner_id=idea["id"], model="test", vector_json=[1], text_hash="idea"),
            Embedding(owner_type="decision", owner_id=decision["id"], model="test", vector_json=[1], text_hash="decision"),
            Embedding(owner_type="open_question", owner_id=question["id"], model="test", vector_json=[1], text_hash="question"),
        ]
    )
    db_session.commit()

    assert delete_task(task["id"], db_session) == {"status": "deleted", "id": task["id"]}
    assert delete_idea(idea["id"], db_session) == {"status": "deleted", "id": idea["id"]}
    assert delete_decision(decision["id"], db_session) == {"status": "deleted", "id": decision["id"]}
    assert delete_question(question["id"], db_session) == {"status": "deleted", "id": question["id"]}
    assert db_session.query(Embedding).count() == 0
