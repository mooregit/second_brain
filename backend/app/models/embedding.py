from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, uuid_str


class Embedding(TimestampMixin, Base):
    __tablename__ = "embeddings"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid_str)
    owner_type: Mapped[str] = mapped_column(String, index=True)
    owner_id: Mapped[str] = mapped_column(String, index=True)
    model: Mapped[str] = mapped_column(String)
    vector_json: Mapped[list[float]] = mapped_column(JSON)
    text_hash: Mapped[str] = mapped_column(String, index=True)

