"""Create note_link table for Obsidian-style linking.

Revision ID: 002_create_note_link
Revises: 001_add_oauth_fields
Create Date: 2026-03-14

Changes:
- Create notelinktargettype enum
- Create note_link table with polymorphic FK columns
- Add composite indexes for query performance
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "002_create_note_link"
down_revision = "001_add_oauth_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create the NoteLinkTargetType enum
    target_type_enum = sa.Enum(
        "note", "document", "artifact", "media", "url",
        name="notelinktargettype",
    )
    target_type_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "note_link",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id", UUID(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column(
            "note_id", UUID(as_uuid=True),
            sa.ForeignKey("note.id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column("label", sa.String(500), nullable=False),
        sa.Column("target_type", target_type_enum, nullable=False),
        sa.Column(
            "target_note_id", UUID(as_uuid=True),
            sa.ForeignKey("note.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "target_document_id", UUID(as_uuid=True),
            sa.ForeignKey("document.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "target_artifact_id", UUID(as_uuid=True),
            sa.ForeignKey("artifact.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("target_url", sa.String(2000), nullable=True),
        sa.Column("media_meta", JSONB, nullable=True),
        sa.Column("position", sa.Integer, nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            nullable=False, server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            nullable=False, server_default=sa.func.now(),
        ),
    )

    # Composite indexes
    op.create_index(
        "ix_note_link_note_target_type",
        "note_link", ["note_id", "target_type"],
    )
    op.create_index(
        "ix_note_link_target_note_id",
        "note_link", ["target_note_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_note_link_target_note_id")
    op.drop_index("ix_note_link_note_target_type")
    op.drop_table("note_link")
    sa.Enum(name="notelinktargettype").drop(op.get_bind(), checkfirst=True)
