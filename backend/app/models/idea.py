from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, uuid_str


class Idea(TimestampMixin, Base):
    __tablename__ = "ideas"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid_str)
    memory_id: Mapped[str] = mapped_column(ForeignKey("memories.id"), index=True)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default="active", index=True)
    source_raw_item_id: Mapped[str] = mapped_column(ForeignKey("raw_items.id"), index=True)

    memory: Mapped["Memory"] = relationship(back_populates="ideas")
    project: Mapped["Project"] = relationship(back_populates="ideas")
