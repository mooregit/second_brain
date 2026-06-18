"""add question answers

Revision ID: 20260618_0006
Revises: 20260616_0005
Create Date: 2026-06-18 20:45:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260618_0006"
down_revision: Union[str, None] = "20260616_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("open_questions", sa.Column("answer_text", sa.Text(), nullable=True))
    op.add_column("open_questions", sa.Column("answer_confidence", sa.Float(), nullable=True))
    op.add_column("open_questions", sa.Column("answer_sources_json", sa.JSON(), nullable=True))
    op.add_column("open_questions", sa.Column("answered_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("open_questions", "answered_at")
    op.drop_column("open_questions", "answer_sources_json")
    op.drop_column("open_questions", "answer_confidence")
    op.drop_column("open_questions", "answer_text")
