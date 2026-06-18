from sqlalchemy import DateTime, Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, uuid_str


class OpenQuestion(TimestampMixin, Base):
    __tablename__ = "open_questions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid_str)
    memory_id: Mapped[str] = mapped_column(ForeignKey("memories.id"), index=True)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    question: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default="open", index=True)
    answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    answer_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    answer_sources_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    answered_at: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)
    source_raw_item_id: Mapped[str] = mapped_column(ForeignKey("raw_items.id"), index=True)

    memory: Mapped["Memory"] = relationship(back_populates="open_questions")
    project: Mapped["Project"] = relationship(back_populates="open_questions")
