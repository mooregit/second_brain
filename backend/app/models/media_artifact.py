from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, uuid_str


class MediaArtifact(TimestampMixin, Base):
    __tablename__ = "media_artifacts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid_str)
    raw_item_id: Mapped[str] = mapped_column(ForeignKey("raw_items.id"), index=True)
    file_asset_id: Mapped[str] = mapped_column(ForeignKey("file_assets.id"), index=True)
    artifact_type: Mapped[str] = mapped_column(String, index=True)
    status: Mapped[str] = mapped_column(String, default="pending", index=True)
    text_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    stored_path: Mapped[str | None] = mapped_column(String, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
