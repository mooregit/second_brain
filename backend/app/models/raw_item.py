from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, uuid_str


class RawItem(TimestampMixin, Base):
    __tablename__ = "raw_items"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid_str)
    source_type: Mapped[str] = mapped_column(String, default="manual", index=True)
    title: Mapped[str] = mapped_column(String)
    body_text: Mapped[str] = mapped_column(Text)
    content_type: Mapped[str] = mapped_column(String, default="text/plain")
    status: Mapped[str] = mapped_column(String, default="new", index=True)
    source_uri: Mapped[str | None] = mapped_column(String, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    memories: Mapped[list["Memory"]] = relationship(back_populates="raw_item", cascade="all, delete-orphan")
    processing_runs: Mapped[list["ProcessingRun"]] = relationship(back_populates="raw_item", cascade="all, delete-orphan")

