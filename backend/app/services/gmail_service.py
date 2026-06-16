import base64
import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import EmailMessage, RawItem
from app.services.extraction_service import ExtractionService
from app.services.settings_service import SettingsService

logger = logging.getLogger(__name__)


class GmailService:
    scopes = ["https://www.googleapis.com/auth/gmail.readonly"]

    def __init__(self, db: Session) -> None:
        self.db = db
        self.env_settings = get_settings()
        self.settings = SettingsService(db)

    async def sync(self, max_results: int = 10, auto_process: bool | None = None, client: Any | None = None) -> dict:
        gmail = client or self._client()
        query = self.settings.get_gmail_query()
        message_refs = self._list_message_refs(gmail, query, max_results)
        imported: list[RawItem] = []
        skipped: list[str] = []

        for message_ref in message_refs:
            message_id = message_ref["id"]
            if self._already_imported(message_id):
                skipped.append(message_id)
                continue
            message = self._get_message(gmail, message_id)
            item = self._import_message(message)
            imported.append(item)

        should_process = self.settings.get_gmail_auto_process() if auto_process is None else auto_process
        processed: list[str] = []
        failed: list[dict] = []
        if should_process:
            for item in imported:
                try:
                    await ExtractionService(self.db).process_item(item)
                    processed.append(item.id)
                except Exception as exc:
                    failed.append({"raw_item_id": item.id, "error": str(exc)})

        return {
            "query": query,
            "imported_count": len(imported),
            "skipped_count": len(skipped),
            "processed_count": len(processed),
            "failed_count": len(failed),
            "imported_items": imported,
            "skipped_message_ids": skipped,
            "processed_item_ids": processed,
            "failures": failed,
        }

    def _client(self) -> Any:
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
        except ImportError as exc:
            raise RuntimeError("Gmail dependencies are not installed. Rebuild the backend image or install google-api-python-client and google-auth-oauthlib.") from exc

        credentials_path = self._path(self.env_settings.gmail_credentials_path)
        token_path = self._path(self.env_settings.gmail_token_path)
        token_path.parent.mkdir(parents=True, exist_ok=True)
        creds = None
        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), self.scopes)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not credentials_path.exists():
                    raise RuntimeError(f"Gmail credentials file not found: {credentials_path}")
                flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), self.scopes)
                creds = self._run_oauth_flow(flow)
            token_path.write_text(creds.to_json(), encoding="utf-8")
        return build("gmail", "v1", credentials=creds)

    def _run_oauth_flow(self, flow: Any) -> Any:
        port = self.env_settings.gmail_oauth_port
        try:
            return flow.run_local_server(
                host="localhost",
                bind_addr="0.0.0.0",
                port=port,
                open_browser=False,
                authorization_prompt_message=(
                    "\nGmail authorization required.\n"
                    "Open this URL in your browser:\n{url}\n\n"
                    f"After approval, Google will redirect to http://localhost:{port}/.\n"
                ),
            )
        except OSError as exc:
            raise RuntimeError(f"Gmail OAuth callback port {port} is unavailable. Set GMAIL_OAUTH_PORT to a free port and expose it in Docker Compose.") from exc
        except Exception as exc:
            logger.exception("Gmail OAuth flow failed")
            raise RuntimeError(f"Gmail OAuth flow failed: {exc}") from exc

    def _path(self, value: str) -> Path:
        path = Path(value).expanduser()
        if path.is_absolute():
            return path
        return (Path.cwd() / path).resolve()

    def _list_message_refs(self, gmail: Any, query: str, max_results: int) -> list[dict]:
        response = gmail.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
        return response.get("messages", [])

    def _get_message(self, gmail: Any, message_id: str) -> dict:
        return gmail.users().messages().get(userId="me", id=message_id, format="full").execute()

    def _already_imported(self, message_id: str) -> bool:
        return self.db.scalar(select(EmailMessage).where(EmailMessage.gmail_message_id == message_id)) is not None

    def _import_message(self, message: dict) -> RawItem:
        headers = self._headers(message)
        subject = headers.get("subject") or "(no subject)"
        from_email = headers.get("from")
        to_email = headers.get("to")
        body_text = self._body_text(message.get("payload", {})) or message.get("snippet") or ""
        sent_at = self._sent_at(headers.get("date"), message.get("internalDate"))
        raw_item = RawItem(
            source_type="gmail",
            title=subject[:200],
            body_text=body_text,
            content_type="message/rfc822",
            source_uri=f"gmail:{message['id']}",
            metadata_json={"thread_id": message.get("threadId"), "label_ids": message.get("labelIds", [])},
        )
        self.db.add(raw_item)
        self.db.flush()
        email = EmailMessage(
            raw_item_id=raw_item.id,
            gmail_message_id=message["id"],
            thread_id=message.get("threadId"),
            from_email=from_email,
            to_email=to_email,
            subject=subject,
            sent_at=sent_at,
            labels_json=message.get("labelIds", []),
            headers_json=headers,
        )
        self.db.add(email)
        self.db.commit()
        self.db.refresh(raw_item)
        return raw_item

    def _headers(self, message: dict) -> dict:
        headers = message.get("payload", {}).get("headers", [])
        return {header["name"].lower(): header.get("value") for header in headers}

    def _body_text(self, payload: dict) -> str:
        if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
            return self._decode(payload["body"]["data"])
        for part in payload.get("parts", []) or []:
            text = self._body_text(part)
            if text:
                return text
        if payload.get("body", {}).get("data"):
            return self._decode(payload["body"]["data"])
        return ""

    def _decode(self, data: str) -> str:
        return base64.urlsafe_b64decode(data.encode("utf-8")).decode("utf-8", errors="replace")

    def _sent_at(self, date_header: str | None, internal_date: str | None) -> datetime | None:
        if date_header:
            try:
                return parsedate_to_datetime(date_header)
            except (TypeError, ValueError):
                pass
        if internal_date:
            try:
                return datetime.fromtimestamp(int(internal_date) / 1000, tz=timezone.utc)
            except ValueError:
                return None
        return None
