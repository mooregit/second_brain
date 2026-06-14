from sqlalchemy import Float, ForeignKey, JSON, String, Table, Text, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, uuid_str


memory_tags = Table(
    "memory_tags",
    Base.metadata,
    Column("memory_id", ForeignKey("memories.id"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id"), primary_key=True),
)


class Memory(TimestampMixin, Base):
    __tablename__ = "memories"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid_str)
    raw_item_id: Mapped[str] = mapped_column(ForeignKey("raw_items.id"), index=True)
    memory_type: Mapped[str] = mapped_column(String)
    summary: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    validated_json: Mapped[dict] = mapped_column(JSON)
    raw_llm_output: Mapped[str] = mapped_column(Text)

    raw_item: Mapped["RawItem"] = relationship(back_populates="memories")
    tags: Mapped[list["Tag"]] = relationship(secondary=memory_tags, back_populates="memories")
    tasks: Mapped[list["Task"]] = relationship(back_populates="memory", cascade="all, delete-orphan")
    ideas: Mapped[list["Idea"]] = relationship(back_populates="memory", cascade="all, delete-orphan")
    decisions: Mapped[list["Decision"]] = relationship(back_populates="memory", cascade="all, delete-orphan")
    open_questions: Mapped[list["OpenQuestion"]] = relationship(back_populates="memory", cascade="all, delete-orphan")
    relationships: Mapped[list["Relationship"]] = relationship(back_populates="memory", cascade="all, delete-orphan")
