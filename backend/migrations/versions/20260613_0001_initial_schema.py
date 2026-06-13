"""initial schema

Revision ID: 20260613_0001
Revises: 
Create Date: 2026-06-13 00:01:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260613_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "projects",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_projects_name"), "projects", ["name"], unique=False)

    op.create_table(
        "raw_items",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("body_text", sa.Text(), nullable=False),
        sa.Column("content_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("source_uri", sa.String(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_raw_items_source_type"), "raw_items", ["source_type"], unique=False)
    op.create_index(op.f("ix_raw_items_status"), "raw_items", ["status"], unique=False)

    op.create_table(
        "tags",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_tags_name"), "tags", ["name"], unique=False)

    op.create_table(
        "people",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_people_name"), "people", ["name"], unique=False)

    op.create_table(
        "embeddings",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("owner_type", sa.String(), nullable=False),
        sa.Column("owner_id", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("vector_json", sa.JSON(), nullable=False),
        sa.Column("text_hash", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_embeddings_owner_id"), "embeddings", ["owner_id"], unique=False)
    op.create_index(op.f("ix_embeddings_owner_type"), "embeddings", ["owner_type"], unique=False)
    op.create_index(op.f("ix_embeddings_text_hash"), "embeddings", ["text_hash"], unique=False)

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("entity_type", sa.String(), nullable=False),
        sa.Column("entity_id", sa.String(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "memories",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("raw_item_id", sa.String(), nullable=False),
        sa.Column("memory_type", sa.String(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("validated_json", sa.JSON(), nullable=False),
        sa.Column("raw_llm_output", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["raw_item_id"], ["raw_items.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_memories_raw_item_id"), "memories", ["raw_item_id"], unique=False)

    op.create_table(
        "processing_runs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("raw_item_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("prompt_version", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("raw_output", sa.Text(), nullable=True),
        sa.Column("parsed_json", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["raw_item_id"], ["raw_items.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_processing_runs_raw_item_id"), "processing_runs", ["raw_item_id"], unique=False)

    op.create_table(
        "email_messages",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("raw_item_id", sa.String(), nullable=False),
        sa.Column("gmail_message_id", sa.String(), nullable=False),
        sa.Column("thread_id", sa.String(), nullable=True),
        sa.Column("from_email", sa.String(), nullable=True),
        sa.Column("to_email", sa.String(), nullable=True),
        sa.Column("subject", sa.String(), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("labels_json", sa.JSON(), nullable=True),
        sa.Column("headers_json", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["raw_item_id"], ["raw_items.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_email_messages_gmail_message_id"), "email_messages", ["gmail_message_id"], unique=False)
    op.create_index(op.f("ix_email_messages_raw_item_id"), "email_messages", ["raw_item_id"], unique=False)

    op.create_table(
        "file_assets",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("raw_item_id", sa.String(), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("stored_path", sa.String(), nullable=False),
        sa.Column("mime_type", sa.String(), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("sha256", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["raw_item_id"], ["raw_items.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_file_assets_raw_item_id"), "file_assets", ["raw_item_id"], unique=False)

    op.create_table(
        "draft_replies",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("email_message_id", sa.String(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("gmail_draft_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["email_message_id"], ["email_messages.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_draft_replies_email_message_id"), "draft_replies", ["email_message_id"], unique=False)

    op.create_table(
        "memory_tags",
        sa.Column("memory_id", sa.String(), nullable=False),
        sa.Column("tag_id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["memory_id"], ["memories.id"]),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"]),
        sa.PrimaryKeyConstraint("memory_id", "tag_id"),
    )

    op.create_table(
        "tasks",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("memory_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("priority", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("source_raw_item_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["memory_id"], ["memories.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["source_raw_item_id"], ["raw_items.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tasks_memory_id"), "tasks", ["memory_id"], unique=False)
    op.create_index(op.f("ix_tasks_project_id"), "tasks", ["project_id"], unique=False)
    op.create_index(op.f("ix_tasks_source_raw_item_id"), "tasks", ["source_raw_item_id"], unique=False)
    op.create_index(op.f("ix_tasks_status"), "tasks", ["status"], unique=False)

    op.create_table(
        "ideas",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("memory_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("source_raw_item_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["memory_id"], ["memories.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["source_raw_item_id"], ["raw_items.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ideas_memory_id"), "ideas", ["memory_id"], unique=False)
    op.create_index(op.f("ix_ideas_project_id"), "ideas", ["project_id"], unique=False)
    op.create_index(op.f("ix_ideas_source_raw_item_id"), "ideas", ["source_raw_item_id"], unique=False)

    op.create_table(
        "decisions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("memory_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
        sa.Column("source_raw_item_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["memory_id"], ["memories.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["source_raw_item_id"], ["raw_items.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_decisions_memory_id"), "decisions", ["memory_id"], unique=False)
    op.create_index(op.f("ix_decisions_project_id"), "decisions", ["project_id"], unique=False)
    op.create_index(op.f("ix_decisions_source_raw_item_id"), "decisions", ["source_raw_item_id"], unique=False)

    op.create_table(
        "open_questions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("memory_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("source_raw_item_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["memory_id"], ["memories.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["source_raw_item_id"], ["raw_items.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_open_questions_memory_id"), "open_questions", ["memory_id"], unique=False)
    op.create_index(op.f("ix_open_questions_project_id"), "open_questions", ["project_id"], unique=False)
    op.create_index(op.f("ix_open_questions_source_raw_item_id"), "open_questions", ["source_raw_item_id"], unique=False)
    op.create_index(op.f("ix_open_questions_status"), "open_questions", ["status"], unique=False)

    op.create_table(
        "relationships",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("memory_id", sa.String(), nullable=False),
        sa.Column("source_label", sa.String(), nullable=False),
        sa.Column("target_label", sa.String(), nullable=False),
        sa.Column("relationship_type", sa.String(), nullable=False),
        sa.Column("source_node_type", sa.String(), nullable=False),
        sa.Column("target_node_type", sa.String(), nullable=False),
        sa.Column("source_raw_item_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["memory_id"], ["memories.id"]),
        sa.ForeignKeyConstraint(["source_raw_item_id"], ["raw_items.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_relationships_memory_id"), "relationships", ["memory_id"], unique=False)
    op.create_index(op.f("ix_relationships_source_raw_item_id"), "relationships", ["source_raw_item_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_relationships_source_raw_item_id"), table_name="relationships")
    op.drop_index(op.f("ix_relationships_memory_id"), table_name="relationships")
    op.drop_table("relationships")
    op.drop_index(op.f("ix_open_questions_status"), table_name="open_questions")
    op.drop_index(op.f("ix_open_questions_source_raw_item_id"), table_name="open_questions")
    op.drop_index(op.f("ix_open_questions_project_id"), table_name="open_questions")
    op.drop_index(op.f("ix_open_questions_memory_id"), table_name="open_questions")
    op.drop_table("open_questions")
    op.drop_index(op.f("ix_decisions_source_raw_item_id"), table_name="decisions")
    op.drop_index(op.f("ix_decisions_project_id"), table_name="decisions")
    op.drop_index(op.f("ix_decisions_memory_id"), table_name="decisions")
    op.drop_table("decisions")
    op.drop_index(op.f("ix_ideas_source_raw_item_id"), table_name="ideas")
    op.drop_index(op.f("ix_ideas_project_id"), table_name="ideas")
    op.drop_index(op.f("ix_ideas_memory_id"), table_name="ideas")
    op.drop_table("ideas")
    op.drop_index(op.f("ix_tasks_status"), table_name="tasks")
    op.drop_index(op.f("ix_tasks_source_raw_item_id"), table_name="tasks")
    op.drop_index(op.f("ix_tasks_project_id"), table_name="tasks")
    op.drop_index(op.f("ix_tasks_memory_id"), table_name="tasks")
    op.drop_table("tasks")
    op.drop_table("memory_tags")
    op.drop_index(op.f("ix_draft_replies_email_message_id"), table_name="draft_replies")
    op.drop_table("draft_replies")
    op.drop_index(op.f("ix_file_assets_raw_item_id"), table_name="file_assets")
    op.drop_table("file_assets")
    op.drop_index(op.f("ix_email_messages_raw_item_id"), table_name="email_messages")
    op.drop_index(op.f("ix_email_messages_gmail_message_id"), table_name="email_messages")
    op.drop_table("email_messages")
    op.drop_index(op.f("ix_processing_runs_raw_item_id"), table_name="processing_runs")
    op.drop_table("processing_runs")
    op.drop_index(op.f("ix_memories_raw_item_id"), table_name="memories")
    op.drop_table("memories")
    op.drop_table("audit_logs")
    op.drop_index(op.f("ix_embeddings_text_hash"), table_name="embeddings")
    op.drop_index(op.f("ix_embeddings_owner_type"), table_name="embeddings")
    op.drop_index(op.f("ix_embeddings_owner_id"), table_name="embeddings")
    op.drop_table("embeddings")
    op.drop_index(op.f("ix_people_name"), table_name="people")
    op.drop_table("people")
    op.drop_index(op.f("ix_tags_name"), table_name="tags")
    op.drop_table("tags")
    op.drop_index(op.f("ix_raw_items_status"), table_name="raw_items")
    op.drop_index(op.f("ix_raw_items_source_type"), table_name="raw_items")
    op.drop_table("raw_items")
    op.drop_index(op.f("ix_projects_name"), table_name="projects")
    op.drop_table("projects")

