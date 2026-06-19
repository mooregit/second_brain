import asyncio
from collections.abc import Generator

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.models import AuditLog, DraftReply, EmailMessage, RawItem
from app.services.draft_reply_service import DraftReplyService
from app.services.ollama_client import OllamaClient
from app.services.retrieval_service import RetrievalService


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


def test_create_draft_reply_stores_draft_and_audit_log(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    raw_item = RawItem(source_type="gmail", title="Question", body_text="Can you send the plan?", status="processed", source_uri="gmail:gmail-1")
    db_session.add(raw_item)
    db_session.flush()
    email = EmailMessage(
        raw_item_id=raw_item.id,
        gmail_message_id="gmail-1",
        thread_id="thread-1",
        from_email="sender@example.com",
        subject="Question",
    )
    db_session.add(email)
    db_session.commit()

    async def fake_retrieve(self: RetrievalService, question: str, limit: int = 5) -> list[dict]:
        return [{"owner_type": "memory", "owner_id": "m1", "text": "Use the saved plan.", "score": 0.9, "title": "Plan", "raw_item_id": raw_item.id}]

    async def fake_generate(self: OllamaClient, model: str, prompt: str) -> str:
        assert "Can you send the plan?" in prompt
        assert "Use the saved plan." in prompt
        return "Here is the plan."

    monkeypatch.setattr(RetrievalService, "retrieve", fake_retrieve)
    monkeypatch.setattr(OllamaClient, "generate", fake_generate)

    draft = asyncio.run(DraftReplyService(db_session).create_draft_reply(email.id, gmail_client=FakeGmailClient()))
    audit_log = db_session.scalar(select(AuditLog).where(AuditLog.entity_id == draft.id))

    assert draft.status == "created_in_gmail"
    assert draft.gmail_draft_id == "draft-1"
    assert draft.body == "Here is the plan."
    assert db_session.get(DraftReply, draft.id) is not None
    assert audit_log is not None
    assert audit_log.action == "gmail_draft_created"
    assert audit_log.metadata_json["gmail_draft_id"] == "draft-1"


class FakeGmailClient:
    def users(self) -> "FakeGmailClient":
        return self

    def drafts(self) -> "FakeGmailClient":
        return self

    def create(self, userId: str, body: dict) -> "FakeRequest":
        assert userId == "me"
        assert body["message"]["threadId"] == "thread-1"
        assert body["message"]["raw"]
        return FakeRequest({"id": "draft-1"})


class FakeRequest:
    def __init__(self, response: dict) -> None:
        self.response = response

    def execute(self) -> dict:
        return self.response
