from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import uuid_str


class DraftReply(Base):
    __tablename__ = "draft_replies"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid_str)
    email_message_id: Mapped[str] = mapped_column(ForeignKey("email_messages.id"), index=True)
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default="draft")
    gmail_draft_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

