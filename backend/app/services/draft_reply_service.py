import base64
from email.mime.text import MIMEText

from sqlalchemy.orm import Session

from app.models import AuditLog, DraftReply, EmailMessage, RawItem
from app.services.ollama_client import OllamaClient
from app.services.retrieval_service import RetrievalService
from app.services.settings_service import SettingsService


class DraftReplyService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = SettingsService(db)
        self.ollama = OllamaClient()
        self.retrieval = RetrievalService(db)

    async def create_draft_reply(self, email_message_id: str, create_in_gmail: bool = True, gmail_client=None) -> DraftReply:
        email = self.db.get(EmailMessage, email_message_id)
        if not email:
            raise ValueError("Email message not found")
        raw_item = self.db.get(RawItem, email.raw_item_id)
        if not raw_item:
            raise ValueError("Source raw item not found")

        body = await self._generate_reply_body(email, raw_item)
        draft = DraftReply(email_message_id=email.id, body=body, status="draft")
        self.db.add(draft)
        self.db.flush()

        if create_in_gmail:
            gmail_draft_id = self._create_gmail_draft(gmail_client, email, body)
            draft.gmail_draft_id = gmail_draft_id
            draft.status = "created_in_gmail"

        self.db.add(
            AuditLog(
                action="gmail_draft_created",
                entity_type="draft_reply",
                entity_id=draft.id,
                metadata_json={
                    "email_message_id": email.id,
                    "gmail_message_id": email.gmail_message_id,
                    "gmail_draft_id": draft.gmail_draft_id,
                    "status": draft.status,
                },
            )
        )
        self.db.commit()
        self.db.refresh(draft)
        return draft

    async def _generate_reply_body(self, email: EmailMessage, raw_item: RawItem) -> str:
        query = f"{email.subject or ''}\n{raw_item.body_text}"
        matches = await self.retrieval.retrieve(query, limit=5)
        context = "\n\n".join(
            f"Source {idx + 1} ({match['owner_type']} {match['owner_id']}):\n{match['text']}"
            for idx, match in enumerate(matches)
        )
        prompt = (
            self._prompt("draft_reply.md")
            + "\n\nEmail subject:\n"
            + (email.subject or "")
            + "\n\nEmail body:\n"
            + raw_item.body_text
            + "\n\nRetrieved context:\n"
            + (context or "No retrieved context.")
            + "\n\nReturn only the draft reply body."
        )
        return (await self.ollama.generate(self.settings.get_ollama_extraction_model(), prompt)).strip()

    def _create_gmail_draft(self, gmail_client, email: EmailMessage, body: str) -> str:
        if gmail_client is None:
            from app.services.gmail_service import GmailService

            gmail_client = GmailService(self.db)._client()
        message = MIMEText(body)
        if email.from_email:
            message["To"] = email.from_email
        if email.subject:
            subject = email.subject if email.subject.lower().startswith("re:") else f"Re: {email.subject}"
            message["Subject"] = subject
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        payload = {"message": {"raw": raw_message}}
        if email.thread_id:
            payload["message"]["threadId"] = email.thread_id
        response = gmail_client.users().drafts().create(userId="me", body=payload).execute()
        return response["id"]

    def _prompt(self, filename: str) -> str:
        return self.settings.env_settings.prompt_dir.joinpath(filename).read_text(encoding="utf-8")
