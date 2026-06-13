from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import uuid_str
from app.models.memory import memory_tags


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid_str)
    name: Mapped[str] = mapped_column(String, unique=True, index=True)

    memories: Mapped[list["Memory"]] = relationship(secondary=memory_tags, back_populates="tags")

