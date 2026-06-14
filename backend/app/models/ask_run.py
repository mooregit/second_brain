from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, uuid_str


class AskRun(TimestampMixin, Base):
    __tablename__ = "ask_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid_str)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    sources_json: Mapped[list] = mapped_column(JSON, default=list)
    saved_raw_item_id: Mapped[str | None] = mapped_column(ForeignKey("raw_items.id"), nullable=True, index=True)

    saved_raw_item: Mapped["RawItem"] = relationship()
