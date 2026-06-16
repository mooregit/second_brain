import base64
import asyncio
from collections.abc import Generator

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.api.routes.items import delete_item
from app.core.database import Base
from app.models import EmailMessage, RawItem
from app.services.gmail_service import GmailService
from app.services.settings_service import SettingsService


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


def test_gmail_sync_imports_messages_once(db_session: Session) -> None:
    SettingsService(db_session).set_gmail_query("label:SecondBrain")
    message = _gmail_message("gmail-1", "Second Brain note", "Remember to test Gmail import.")
    client = FakeGmailClient([message])

    first = asyncio.run(GmailService(db_session).sync(auto_process=False, client=client))
    assert first["imported_count"] == 1
    assert first["skipped_count"] == 0
    assert first["processed_count"] == 0

    item = db_session.scalar(select(RawItem).where(RawItem.source_type == "gmail"))
    assert item is not None
    assert item.title == "Second Brain note"
    assert item.body_text == "Remember to test Gmail import."

    email = db_session.scalar(select(EmailMessage).where(EmailMessage.gmail_message_id == "gmail-1"))
    assert email is not None
    assert email.raw_item_id == item.id
    assert email.subject == "Second Brain note"

    second = asyncio.run(GmailService(db_session).sync(auto_process=False, client=client))
    assert second["imported_count"] == 0
    assert second["skipped_count"] == 1

    delete_response = delete_item(item.id, db_session)
    assert delete_response["status"] == "deleted"
    assert db_session.scalar(select(EmailMessage).where(EmailMessage.gmail_message_id == "gmail-1")) is None

    third = asyncio.run(GmailService(db_session).sync(auto_process=False, client=client))
    assert third["imported_count"] == 1
    assert third["skipped_count"] == 0


def test_gmail_oauth_flow_does_not_try_to_open_browser(db_session: Session) -> None:
    flow = FakeOAuthFlow()
    GmailService(db_session)._run_oauth_flow(flow)

    assert flow.kwargs["open_browser"] is False
    assert flow.kwargs["bind_addr"] == "0.0.0.0"
    assert flow.kwargs["port"] == 8090


def _gmail_message(message_id: str, subject: str, body: str) -> dict:
    encoded_body = base64.urlsafe_b64encode(body.encode("utf-8")).decode("utf-8")
    return {
        "id": message_id,
        "threadId": "thread-1",
        "labelIds": ["Label_SecondBrain"],
        "internalDate": "1710000000000",
        "snippet": body,
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "Subject", "value": subject},
                {"name": "From", "value": "sender@example.com"},
                {"name": "To", "value": "me@example.com"},
            ],
            "body": {"data": encoded_body},
        },
    }


class FakeGmailClient:
    def __init__(self, messages: list[dict]) -> None:
        self._messages = {message["id"]: message for message in messages}

    def users(self) -> "FakeGmailClient":
        return self

    def messages(self) -> "FakeGmailClient":
        return self

    def list(self, userId: str, q: str, maxResults: int) -> "FakeRequest":
        return FakeRequest({"messages": [{"id": message_id} for message_id in list(self._messages)[:maxResults]]})

    def get(self, userId: str, id: str, format: str) -> "FakeRequest":
        return FakeRequest(self._messages[id])


class FakeRequest:
    def __init__(self, response: dict) -> None:
        self.response = response

    def execute(self) -> dict:
        return self.response


class FakeOAuthFlow:
    def __init__(self) -> None:
        self.kwargs = {}

    def run_local_server(self, **kwargs) -> object:
        self.kwargs = kwargs
        return object()
