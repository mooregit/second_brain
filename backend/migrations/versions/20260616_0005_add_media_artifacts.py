"""add media artifacts

Revision ID: 20260616_0005
Revises: 20260614_0004
Create Date: 2026-06-16 20:15:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260616_0005"
down_revision: Union[str, None] = "20260614_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "media_artifacts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("raw_item_id", sa.String(), nullable=False),
        sa.Column("file_asset_id", sa.String(), nullable=False),
        sa.Column("artifact_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("text_content", sa.Text(), nullable=True),
        sa.Column("stored_path", sa.String(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["file_asset_id"], ["file_assets.id"]),
        sa.ForeignKeyConstraint(["raw_item_id"], ["raw_items.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_media_artifacts_artifact_type"), "media_artifacts", ["artifact_type"], unique=False)
    op.create_index(op.f("ix_media_artifacts_file_asset_id"), "media_artifacts", ["file_asset_id"], unique=False)
    op.create_index(op.f("ix_media_artifacts_raw_item_id"), "media_artifacts", ["raw_item_id"], unique=False)
    op.create_index(op.f("ix_media_artifacts_status"), "media_artifacts", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_media_artifacts_status"), table_name="media_artifacts")
    op.drop_index(op.f("ix_media_artifacts_raw_item_id"), table_name="media_artifacts")
    op.drop_index(op.f("ix_media_artifacts_file_asset_id"), table_name="media_artifacts")
    op.drop_index(op.f("ix_media_artifacts_artifact_type"), table_name="media_artifacts")
    op.drop_table("media_artifacts")
