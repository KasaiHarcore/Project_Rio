"""Create flashcard_deck, flashcard, automation, and audio_overview tables.

Revision ID: 006_flashcard_automation
Revises: 005_note_thread_set_null
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "006_flashcard_automation"
down_revision = "005_note_thread_set_null"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Enums ──
    flashcard_source = sa.Enum("agent", "user", name="flashcardsource")
    flashcard_source.create(op.get_bind(), checkfirst=True)

    automation_delivery = sa.Enum("chat_thread", "note", "notification", name="automationdelivery")
    automation_delivery.create(op.get_bind(), checkfirst=True)

    audio_format = sa.Enum("summary", "dialogue", "lecture", name="audioformat")
    audio_format.create(op.get_bind(), checkfirst=True)

    audio_source_type = sa.Enum("notes", "documents", "flashcards", name="audiosourcetype")
    audio_source_type.create(op.get_bind(), checkfirst=True)

    audio_status = sa.Enum("pending", "generating", "ready", "failed", name="audiostatus")
    audio_status.create(op.get_bind(), checkfirst=True)

    # ── flashcard_deck ──
    op.create_table(
        "flashcard_deck",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True),
                  sa.ForeignKey("user.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
    )

    # ── flashcard ──
    op.create_table(
        "flashcard",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True),
                  sa.ForeignKey("user.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("deck_id", UUID(as_uuid=True),
                  sa.ForeignKey("flashcard_deck.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("note_id", UUID(as_uuid=True),
                  sa.ForeignKey("note.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("front", sa.Text, nullable=False),
        sa.Column("back", sa.Text, nullable=False),
        sa.Column("ease_factor", sa.Float, nullable=False, server_default="2.5"),
        sa.Column("interval_days", sa.Integer, nullable=False, server_default="0"),
        sa.Column("repetitions", sa.Integer, nullable=False, server_default="0"),
        sa.Column("next_review", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
        sa.Column("source", flashcard_source, nullable=False, server_default="user"),
        sa.Column("tags", JSONB, nullable=False, server_default="[]"),
        sa.Column("is_suspended", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("total_reviews", sa.Integer, nullable=False, server_default="0"),
        sa.Column("correct_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("streak", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_flashcard_user_next_review", "flashcard",
                    ["user_id", "next_review"])
    op.create_index("ix_flashcard_deck_next_review", "flashcard",
                    ["deck_id", "next_review"])

    # ── automation ──
    op.create_table(
        "automation",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True),
                  sa.ForeignKey("user.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True, server_default=""),
        sa.Column("cron_expression", sa.String(100), nullable=False),
        sa.Column("timezone", sa.String(50), nullable=False, server_default="UTC"),
        sa.Column("agent_instruction", sa.Text, nullable=False),
        sa.Column("agent_mode", sa.String(20), nullable=False, server_default="chat"),
        sa.Column("result_delivery", automation_delivery, nullable=False,
                  server_default="notification"),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("run_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("max_runs", sa.Integer, nullable=True),
        sa.Column("last_result", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_automation_user_enabled", "automation",
                    ["user_id", "enabled"])
    op.create_index("ix_automation_next_run", "automation",
                    ["next_run_at"])

    # ── audio_overview ──
    op.create_table(
        "audio_overview",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True),
                  sa.ForeignKey("user.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("source_ids", JSONB, nullable=False, server_default="[]"),
        sa.Column("source_type", audio_source_type, nullable=False, server_default="notes"),
        sa.Column("transcript", sa.Text, nullable=True),
        sa.Column("audio_path", sa.String(500), nullable=True),
        sa.Column("duration_seconds", sa.Integer, nullable=True),
        sa.Column("format", audio_format, nullable=False, server_default="summary"),
        sa.Column("status", audio_status, nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_audio_overview_user_status", "audio_overview",
                    ["user_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_audio_overview_user_status")
    op.drop_table("audio_overview")
    op.drop_index("ix_automation_next_run")
    op.drop_index("ix_automation_user_enabled")
    op.drop_table("automation")

    op.drop_index("ix_flashcard_deck_next_review")
    op.drop_index("ix_flashcard_user_next_review")
    op.drop_table("flashcard")
    op.drop_table("flashcard_deck")

    sa.Enum(name="flashcardsource").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="automationdelivery").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="audioformat").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="audiosourcetype").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="audiostatus").drop(op.get_bind(), checkfirst=True)
