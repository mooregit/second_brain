"""add idea status

Revision ID: 20260614_0002
Revises: 20260613_0001
Create Date: 2026-06-14 00:02:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260614_0002"
down_revision: Union[str, None] = "20260613_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("ideas", sa.Column("status", sa.String(), nullable=False, server_default="active"))
    op.create_index(op.f("ix_ideas_status"), "ideas", ["status"], unique=False)
    op.alter_column("ideas", "status", server_default=None)


def downgrade() -> None:
    op.drop_index(op.f("ix_ideas_status"), table_name="ideas")
    op.drop_column("ideas", "status")
