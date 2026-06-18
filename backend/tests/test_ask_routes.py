import asyncio
from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.routes.ask import save_ask_result
from app.core.database import Base
from app.models import AskRun, OpenQuestion
from app.schemas.ask import AskSaveRequest
from app.services.ask_service import AskService
from app.services.embedding_service import EmbeddingService
from app.services.ollama_client import OllamaClient
from app.services.retrieval_service import RetrievalService


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


def test_save_ask_result_as_open_question_creates_traceable_memory(db_session: Session) -> None:
    ask_run = AskRun(question="What is unresolved?", answer="You need to choose the Docker commands.", sources_json=[])
    db_session.add(ask_run)
    db_session.commit()

    saved = asyncio.run(
        save_ask_result(
            ask_run.id,
            AskSaveRequest(save_as="open_question", title="Which Docker commands should be shown?", body="From Ask"),
            db_session,
        )
    )

    assert saved.entity_type == "open_question"
    question = db_session.get(OpenQuestion, saved.entity_id)
    assert question is not None
    assert question.memory_id == saved.memory_id
    assert question.source_raw_item_id == saved.raw_item_id
    assert question.question == "Which Docker commands should be shown?"

    db_session.refresh(ask_run)
    assert ask_run.saved_raw_item_id == saved.raw_item_id


def test_ask_returns_insufficient_context_without_calling_llm(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    async def empty_retrieve(self: RetrievalService, question: str, limit: int = 6) -> list[dict]:
        return []

    async def fail_generate(self: OllamaClient, model: str, prompt: str) -> str:
        raise AssertionError("Ollama should not be called when retrieval returns no context")

    monkeypatch.setattr(RetrievalService, "retrieve", empty_retrieve)
    monkeypatch.setattr(OllamaClient, "generate", fail_generate)

    response = asyncio.run(AskService(db_session).ask("What do I know about BetRight?"))

    assert response.answer == "There is not enough stored context to answer that yet."
    assert response.sources == []
    assert response.ask_run_id is not None
    stored = db_session.get(AskRun, response.ask_run_id)
    assert stored is not None
    assert stored.question == "What do I know about BetRight?"
    assert stored.answer == response.answer
    assert stored.sources_json == []
