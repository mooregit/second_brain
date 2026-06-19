import base64
import asyncio
from collections.abc import Generator

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.api.routes.items import delete_item
from app.core.database import Base
from app.models import EmailMessage, FileAsset, RawItem
from app.services.gmail_poller import GmailPoller
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
    assert first["auto_process"] is False

    latest_sync = SettingsService(db_session).get_gmail_last_sync_result()
    assert latest_sync is not None
    assert latest_sync["status"] == "succeeded"
    assert latest_sync["query"] == "label:SecondBrain"
    assert latest_sync["imported_count"] == 1
    assert latest_sync["processed_count"] == 0

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


def test_gmail_sync_stores_video_attachments(db_session: Session, tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    SettingsService(db_session).set_gmail_query("label:SecondBrain")
    video_bytes = b"fake video bytes"
    message = _gmail_message_with_video("gmail-video-1", "Video note", "Please parse this video.", "demo clip.mp4", video_bytes)
    client = FakeGmailClient([message], attachments={"attachment-1": video_bytes})
    monkeypatch.setattr(GmailService, "_attachment_directory", lambda self, message_id: tmp_path / "uploads" / message_id)

    result = asyncio.run(GmailService(db_session).sync(auto_process=False, client=client))

    assert result["imported_count"] == 1
    item = db_session.scalar(select(RawItem).where(RawItem.source_type == "gmail"))
    assert item is not None
    assert "Video attachments:" in item.body_text
    assert "demo clip.mp4 (video/mp4" in item.body_text
    assert "transcript and frame analysis pending" in item.body_text

    asset = db_session.scalar(select(FileAsset).where(FileAsset.raw_item_id == item.id))
    assert asset is not None
    assert asset.filename == "demo_clip.mp4"
    assert asset.mime_type == "video/mp4"
    assert asset.size_bytes == len(video_bytes)
    assert asset.sha256 is not None
    assert (tmp_path / "uploads" / "gmail-video-1" / "demo_clip.mp4").read_bytes() == video_bytes


def test_gmail_sync_strips_trailing_sender_signature(db_session: Session) -> None:
    SettingsService(db_session).set_gmail_query("label:SecondBrain")
    body = "https://saharamediterraneancuisine.shop/\n\nRussell G. Moore"
    message = _gmail_message("gmail-signature-1", "Website needs work", body, from_email="Russell G. Moore <russell@example.com>")
    client = FakeGmailClient([message])

    result = asyncio.run(GmailService(db_session).sync(auto_process=False, client=client))

    assert result["imported_count"] == 1
    item = db_session.scalar(select(RawItem).where(RawItem.source_type == "gmail"))
    assert item is not None
    assert item.body_text == "https://saharamediterraneancuisine.shop/"


def test_gmail_sync_downloads_google_drive_video_links(db_session: Session, tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    SettingsService(db_session).set_gmail_query("label:SecondBrain")
    video_bytes = b"drive video bytes"
    body = """
    [image: Video File]
    <https://drive.google.com/file/d/drive-file-1>
    v15044gf0000d8oa03nog65geogdhmjg.mp4
    <https://drive.google.com/file/d/drive-file-1>
    """
    message = _gmail_message("gmail-drive-1", "Workflow Imagination", body)
    client = FakeGmailClient(
        [message],
        drive_files={
            "drive-file-1": {
                "metadata": {
                    "id": "drive-file-1",
                    "name": "v15044gf0000d8oa03nog65geogdhmjg.mp4",
                    "mimeType": "video/mp4",
                    "size": str(len(video_bytes)),
                },
                "content": video_bytes,
            }
        },
    )
    monkeypatch.setattr(GmailService, "_drive_attachment_directory", lambda self, file_id: tmp_path / "drive" / file_id)

    result = asyncio.run(GmailService(db_session).sync(auto_process=False, client=client))

    assert result["imported_count"] == 1
    item = db_session.scalar(select(RawItem).where(RawItem.source_type == "gmail"))
    assert item is not None
    assert "Google Drive file drive-file-1" in item.body_text
    assert "Video parsing status" in item.body_text

    asset = db_session.scalar(select(FileAsset).where(FileAsset.raw_item_id == item.id))
    assert asset is not None
    assert asset.filename == "v15044gf0000d8oa03nog65geogdhmjg.mp4"
    assert asset.mime_type == "video/mp4"
    assert asset.size_bytes == len(video_bytes)
    assert (tmp_path / "drive" / "drive-file-1" / "v15044gf0000d8oa03nog65geogdhmjg.mp4").read_bytes() == video_bytes


def test_gmail_oauth_flow_does_not_try_to_open_browser(db_session: Session) -> None:
    flow = FakeOAuthFlow()
    GmailService(db_session)._run_oauth_flow(flow)

    assert flow.kwargs["open_browser"] is False
    assert flow.kwargs["bind_addr"] == "0.0.0.0"
    assert flow.kwargs["port"] == 8090


def test_gmail_poller_skips_when_gmail_disabled(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    called = False

    async def fake_sync(self: GmailService, max_results: int = 10, auto_process: bool | None = None, client=None) -> dict:
        nonlocal called
        called = True
        return {}

    monkeypatch.setattr(GmailService, "sync", fake_sync)

    result = asyncio.run(GmailPoller(lambda: db_session).poll_once())

    assert result == {"status": "disabled", "synced": False}
    assert called is False


def test_gmail_poller_syncs_when_gmail_enabled(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    SettingsService(db_session).set_gmail_enabled(True)

    async def fake_sync(self: GmailService, max_results: int = 10, auto_process: bool | None = None, client=None) -> dict:
        return {
            "status": "succeeded",
            "query": "label:SecondBrain",
            "auto_process": True,
            "max_results": max_results,
            "synced_at": "2026-06-19T00:00:00+00:00",
            "imported_count": 0,
            "skipped_count": 0,
            "processed_count": 0,
            "failed_count": 0,
            "imported_items": [],
            "skipped_message_ids": [],
            "processed_item_ids": [],
            "failures": [],
        }

    monkeypatch.setattr(GmailService, "sync", fake_sync)

    result = asyncio.run(GmailPoller(lambda: db_session, max_results=3).poll_once())

    assert result["synced"] is True
    assert result["status"] == "succeeded"
    assert result["max_results"] == 3
    assert "imported_items" not in result


def _gmail_message(message_id: str, subject: str, body: str, from_email: str = "sender@example.com") -> dict:
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
                {"name": "From", "value": from_email},
                {"name": "To", "value": "me@example.com"},
            ],
            "body": {"data": encoded_body},
        },
    }


def _gmail_message_with_video(message_id: str, subject: str, body: str, filename: str, video_bytes: bytes) -> dict:
    encoded_body = base64.urlsafe_b64encode(body.encode("utf-8")).decode("utf-8")
    return {
        "id": message_id,
        "threadId": "thread-1",
        "labelIds": ["Label_SecondBrain"],
        "internalDate": "1710000000000",
        "snippet": body,
        "payload": {
            "mimeType": "multipart/mixed",
            "headers": [
                {"name": "Subject", "value": subject},
                {"name": "From", "value": "sender@example.com"},
                {"name": "To", "value": "me@example.com"},
            ],
            "parts": [
                {"mimeType": "text/plain", "body": {"data": encoded_body}},
                {
                    "mimeType": "video/mp4",
                    "filename": filename,
                    "body": {
                        "attachmentId": "attachment-1",
                        "size": len(video_bytes),
                    },
                },
            ],
        },
    }


class FakeGmailClient:
    def __init__(self, messages: list[dict], attachments: dict[str, bytes] | None = None, drive_files: dict[str, dict] | None = None) -> None:
        self._messages = {message["id"]: message for message in messages}
        self._attachments = attachments or {}
        self._drive_files = drive_files or {}

    def users(self) -> "FakeGmailClient":
        return self

    def messages(self) -> "FakeGmailClient":
        return self

    def list(self, userId: str, q: str, maxResults: int) -> "FakeRequest":
        return FakeRequest({"messages": [{"id": message_id} for message_id in list(self._messages)[:maxResults]]})

    def get(self, userId: str, id: str, format: str) -> "FakeRequest":
        return FakeRequest(self._messages[id])

    def attachments(self) -> "FakeAttachmentResource":
        return FakeAttachmentResource(self._attachments)

    def drive(self) -> "FakeDriveClient | None":
        if not self._drive_files:
            return None
        return FakeDriveClient(self._drive_files)


class FakeAttachmentResource:
    def __init__(self, attachments: dict[str, bytes]) -> None:
        self._attachments = attachments

    def get(self, userId: str, messageId: str, id: str) -> "FakeRequest":
        return FakeRequest({"data": base64.urlsafe_b64encode(self._attachments[id]).decode("utf-8")})


class FakeDriveClient:
    def __init__(self, drive_files: dict[str, dict]) -> None:
        self._drive_files = drive_files

    def files(self) -> "FakeDriveFiles":
        return FakeDriveFiles(self._drive_files)


class FakeDriveFiles:
    def __init__(self, drive_files: dict[str, dict]) -> None:
        self._drive_files = drive_files

    def get(self, fileId: str, fields: str) -> "FakeRequest":
        return FakeRequest(self._drive_files[fileId]["metadata"])

    def get_media(self, fileId: str) -> "FakeRequest":
        return FakeRequest(self._drive_files[fileId]["content"])


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
