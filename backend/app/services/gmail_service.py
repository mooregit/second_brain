import base64
import hashlib
import json
import logging
from datetime import datetime, timezone
from email.utils import parseaddr, parsedate_to_datetime
from pathlib import Path
from re import finditer, sub
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import EmailMessage, FileAsset, RawItem
from app.services.extraction_service import ExtractionService
from app.services.settings_service import SettingsService

logger = logging.getLogger(__name__)


class GmailService:
    scopes = ["https://www.googleapis.com/auth/gmail.readonly", "https://www.googleapis.com/auth/drive.readonly"]

    def __init__(self, db: Session) -> None:
        self.db = db
        self.env_settings = get_settings()
        self.settings = SettingsService(db)

    async def sync(self, max_results: int = 10, auto_process: bool | None = None, client: Any | None = None) -> dict:
        gmail = client or self._client()
        drive = self._drive_client_from_gmail(gmail) if client else self._drive_client()
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
            item = self._import_message(gmail, drive, message)
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

        result = {
            "status": "succeeded" if not failed else "completed_with_failures",
            "query": query,
            "auto_process": should_process,
            "max_results": max_results,
            "synced_at": datetime.now(timezone.utc).isoformat(),
            "imported_count": len(imported),
            "skipped_count": len(skipped),
            "processed_count": len(processed),
            "failed_count": len(failed),
            "imported_items": imported,
            "skipped_message_ids": skipped,
            "processed_item_ids": processed,
            "failures": failed,
        }
        self.settings.set_gmail_last_sync_result(
            {
                key: value
                for key, value in result.items()
                if key not in {"imported_items"}
            }
        )
        return result

    def _client(self) -> Any:
        return self._google_service("gmail", "v1")

    def _drive_client(self) -> Any:
        return self._google_service("drive", "v3")

    def _google_service(self, service_name: str, version: str) -> Any:
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
            token_info = json.loads(token_path.read_text(encoding="utf-8"))
            token_scopes = token_info.get("scopes") or token_info.get("scope", "").split()
            if token_scopes and not set(self.scopes).issubset(set(token_scopes)):
                creds = None
            else:
                creds = Credentials.from_authorized_user_info(token_info, self.scopes)
                if not creds.has_scopes(self.scopes):
                    creds = None
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not credentials_path.exists():
                    raise RuntimeError(f"Gmail credentials file not found: {credentials_path}")
                flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), self.scopes)
                creds = self._run_oauth_flow(flow)
            token_path.write_text(creds.to_json(), encoding="utf-8")
        return build(service_name, version, credentials=creds)

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

    def _get_attachment(self, gmail: Any, message_id: str, attachment_id: str) -> dict:
        return gmail.users().messages().attachments().get(userId="me", messageId=message_id, id=attachment_id).execute()

    def _drive_client_from_gmail(self, gmail: Any) -> Any | None:
        if hasattr(gmail, "drive"):
            return gmail.drive()
        return None

    def _already_imported(self, message_id: str) -> bool:
        return self.db.scalar(select(EmailMessage).where(EmailMessage.gmail_message_id == message_id)) is not None

    def _import_message(self, gmail: Any, drive: Any | None, message: dict) -> RawItem:
        headers = self._headers(message)
        subject = headers.get("subject") or "(no subject)"
        from_email = headers.get("from")
        to_email = headers.get("to")
        body_text = self._body_text(message.get("payload", {})) or message.get("snippet") or ""
        body_text = self._clean_body_text(body_text, from_email)
        sent_at = self._sent_at(headers.get("date"), message.get("internalDate"))
        video_parts = self._video_attachment_parts(message.get("payload", {}))
        drive_video_parts = self._drive_video_parts(drive, body_text) if drive else []
        if video_parts or drive_video_parts:
            body_text = self._body_text_with_attachments(body_text, video_parts, drive_video_parts)
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
        for part in video_parts:
            self._store_video_attachment(gmail, message["id"], raw_item.id, part)
        for part in drive_video_parts:
            self._store_drive_video(raw_item.id, part)
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

    def _video_attachment_parts(self, payload: dict) -> list[dict]:
        parts: list[dict] = []
        self._collect_video_attachment_parts(payload, parts)
        return parts

    def _collect_video_attachment_parts(self, payload: dict, parts: list[dict]) -> None:
        mime_type = payload.get("mimeType")
        filename = payload.get("filename")
        body = payload.get("body", {})
        attachment_id = body.get("attachmentId")
        if filename and attachment_id and mime_type and mime_type.startswith("video/"):
            parts.append(
                {
                    "attachment_id": attachment_id,
                    "filename": filename,
                    "mime_type": mime_type,
                    "size": body.get("size"),
                }
            )
        for part in payload.get("parts", []) or []:
            self._collect_video_attachment_parts(part, parts)

    def _body_text_with_attachments(self, body_text: str, video_parts: list[dict], drive_video_parts: list[dict]) -> str:
        lines = [body_text.strip()] if body_text.strip() else []
        lines.append("")
        lines.append("Video attachments:")
        for part in video_parts:
            size = f", {part['size']} bytes" if part.get("size") is not None else ""
            lines.append(f"- {part['filename']} ({part['mime_type']}{size})")
        for part in drive_video_parts:
            size = f", {part['size']} bytes" if part.get("size") is not None else ""
            lines.append(f"- {part['filename']} ({part['mime_type']}{size}, Google Drive file {part['file_id']})")
        lines.append("")
        lines.append("Video parsing status: attachment stored locally; transcript and frame analysis pending.")
        return "\n".join(lines).strip()

    def _clean_body_text(self, body_text: str, from_email: str | None) -> str:
        sender_name, sender_email = parseaddr(from_email or "")
        sender_labels = {self._normalize_label(sender_name), self._normalize_label(sender_email)}
        sender_labels.discard("")
        lines = [line.rstrip() for line in body_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]

        while lines and not lines[-1].strip():
            lines.pop()
        while lines and self._is_signature_line(lines[-1], sender_labels):
            lines.pop()
            while lines and not lines[-1].strip():
                lines.pop()
        return "\n".join(lines).strip()

    def _is_signature_line(self, line: str, sender_labels: set[str]) -> bool:
        stripped = line.strip().strip("*_")
        normalized = self._normalize_label(stripped)
        if normalized in sender_labels:
            return True
        if stripped in {"--", "Sent from my iPhone", "Sent from my Android"}:
            return True
        return False

    def _normalize_label(self, value: str) -> str:
        return " ".join(value.lower().strip().strip("<>").split())

    def _drive_video_parts(self, drive: Any, body_text: str) -> list[dict]:
        parts = []
        for file_id in self._drive_file_ids(body_text):
            try:
                metadata = drive.files().get(fileId=file_id, fields="id,name,mimeType,size").execute()
            except Exception as exc:
                logger.warning("Failed to read Google Drive file metadata for %s: %s", file_id, exc)
                continue
            mime_type = metadata.get("mimeType")
            if not mime_type or not mime_type.startswith("video/"):
                continue
            try:
                content = self._download_drive_file(drive, file_id)
            except Exception as exc:
                logger.warning("Failed to download Google Drive file %s: %s", file_id, exc)
                continue
            parts.append(
                {
                    "file_id": file_id,
                    "filename": metadata.get("name") or f"{file_id}.mp4",
                    "mime_type": mime_type,
                    "size": int(metadata["size"]) if metadata.get("size") else None,
                    "content": content,
                }
            )
        return parts

    def _drive_file_ids(self, body_text: str) -> list[str]:
        file_ids = []
        for match in finditer(r"https?://drive\.google\.com/file/d/([^/\s<>]+)", body_text):
            file_id = match.group(1)
            if file_id not in file_ids:
                file_ids.append(file_id)
        return file_ids

    def _download_drive_file(self, drive: Any, file_id: str) -> bytes:
        content = drive.files().get_media(fileId=file_id).execute()
        if isinstance(content, bytes):
            return content
        if isinstance(content, str):
            return content.encode("utf-8")
        return bytes(content)

    def _store_video_attachment(self, gmail: Any, message_id: str, raw_item_id: str, part: dict) -> FileAsset:
        attachment = self._get_attachment(gmail, message_id, part["attachment_id"])
        content = self._decode_bytes(attachment["data"])
        directory = self._attachment_directory(message_id)
        directory.mkdir(parents=True, exist_ok=True)
        filename = self._safe_filename(part["filename"])
        path = directory / filename
        path.write_bytes(content)
        sha256 = hashlib.sha256(content).hexdigest()
        asset = FileAsset(
            raw_item_id=raw_item_id,
            filename=filename,
            stored_path=str(path),
            mime_type=part["mime_type"],
            size_bytes=len(content),
            sha256=sha256,
        )
        self.db.add(asset)
        return asset

    def _store_drive_video(self, raw_item_id: str, part: dict) -> FileAsset:
        content = part["content"]
        directory = self._drive_attachment_directory(part["file_id"])
        directory.mkdir(parents=True, exist_ok=True)
        filename = self._safe_filename(part["filename"])
        path = directory / filename
        path.write_bytes(content)
        sha256 = hashlib.sha256(content).hexdigest()
        asset = FileAsset(
            raw_item_id=raw_item_id,
            filename=filename,
            stored_path=str(path),
            mime_type=part["mime_type"],
            size_bytes=len(content),
            sha256=sha256,
        )
        self.db.add(asset)
        return asset

    def _drive_attachment_directory(self, file_id: str) -> Path:
        return (Path.cwd() / "../data/uploads/drive" / self._safe_filename(file_id)).resolve()

    def _attachment_directory(self, message_id: str) -> Path:
        return (Path.cwd() / "../data/uploads/gmail" / self._safe_filename(message_id)).resolve()

    def _safe_filename(self, value: str) -> str:
        cleaned = sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
        return cleaned.strip("._") or "attachment"

    def _decode(self, data: str) -> str:
        return self._decode_bytes(data).decode("utf-8", errors="replace")

    def _decode_bytes(self, data: str) -> bytes:
        padding = "=" * (-len(data) % 4)
        return base64.urlsafe_b64decode(f"{data}{padding}".encode("utf-8"))

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
