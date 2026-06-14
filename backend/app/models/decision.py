from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, uuid_str


class Decision(TimestampMixin, Base):
    __tablename__ = "decisions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid_str)
    memory_id: Mapped[str] = mapped_column(ForeignKey("memories.id"), index=True)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    source_raw_item_id: Mapped[str] = mapped_column(ForeignKey("raw_items.id"), index=True)

    memory: Mapped["Memory"] = relationship(back_populates="decisions")
    project: Mapped["Project"] = relationship(back_populates="decisions")
