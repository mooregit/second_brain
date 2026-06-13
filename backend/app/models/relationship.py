from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, uuid_str


class Relationship(TimestampMixin, Base):
    __tablename__ = "relationships"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid_str)
    memory_id: Mapped[str] = mapped_column(ForeignKey("memories.id"), index=True)
    source_label: Mapped[str] = mapped_column(String)
    target_label: Mapped[str] = mapped_column(String)
    relationship_type: Mapped[str] = mapped_column(String)
    source_node_type: Mapped[str] = mapped_column(String, default="entity")
    target_node_type: Mapped[str] = mapped_column(String, default="entity")
    source_raw_item_id: Mapped[str] = mapped_column(ForeignKey("raw_items.id"), index=True)

    memory: Mapped["Memory"] = relationship(back_populates="relationships")

