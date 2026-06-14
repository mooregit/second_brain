"""add ask runs

Revision ID: 20260614_0003
Revises: 20260614_0002
Create Date: 2026-06-14 00:03:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260614_0003"
down_revision: Union[str, None] = "20260614_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ask_runs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("sources_json", sa.JSON(), nullable=False),
        sa.Column("saved_raw_item_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["saved_raw_item_id"], ["raw_items.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ask_runs_saved_raw_item_id"), "ask_runs", ["saved_raw_item_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_ask_runs_saved_raw_item_id"), table_name="ask_runs")
    op.drop_table("ask_runs")
