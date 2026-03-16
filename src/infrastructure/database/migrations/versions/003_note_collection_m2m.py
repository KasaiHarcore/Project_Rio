"""Add note_collection_membership junction table for M2M.

Revision ID: 003_note_collection_m2m
Revises: 002_create_note_link
Create Date: 2026-03-16

Changes:
- Create note_collection_membership junction table (note_id, collection_id, added_at)
- Migrate existing note.collection_id data into junction table
- Drop note.collection_id column and its index
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "003_note_collection_m2m"
down_revision = "002_create_note_link"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create the junction table
    op.create_table(
        "note_collection_membership",
        sa.Column(
            "note_id", UUID(as_uuid=True),
            sa.ForeignKey("note.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "collection_id", UUID(as_uuid=True),
            sa.ForeignKey("note_collection.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "added_at", sa.DateTime(timezone=True),
            nullable=False, server_default=sa.func.now(),
        ),
    )

    op.create_index("ix_ncm_note_id", "note_collection_membership", ["note_id"])
    op.create_index("ix_ncm_collection_id", "note_collection_membership", ["collection_id"])

    # 2. Migrate existing data: copy note.collection_id into junction table
    op.execute(
        """
        INSERT INTO note_collection_membership (note_id, collection_id, added_at)
        SELECT id, collection_id, COALESCE(updated_at, NOW())
        FROM note
        WHERE collection_id IS NOT NULL
        """
    )

    # 3. Drop the old collection_id column and its index
    op.drop_index("ix_note_collection_id_fk", table_name="note")
    op.drop_constraint("fk_note_collection_id_note_collection", "note", type_="foreignkey")
    op.drop_column("note", "collection_id")


def downgrade() -> None:
    # Re-add collection_id column
    op.add_column(
        "note",
        sa.Column(
            "collection_id", UUID(as_uuid=True),
            sa.ForeignKey("note_collection.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_note_collection_id_fk", "note", ["collection_id"])

    # Migrate data back: pick the first collection for each note
    op.execute(
        """
        UPDATE note
        SET collection_id = ncm.collection_id
        FROM (
            SELECT DISTINCT ON (note_id) note_id, collection_id
            FROM note_collection_membership
            ORDER BY note_id, added_at ASC
        ) ncm
        WHERE note.id = ncm.note_id
        """
    )

    # Drop junction table
    op.drop_index("ix_ncm_collection_id", table_name="note_collection_membership")
    op.drop_index("ix_ncm_note_id", table_name="note_collection_membership")
    op.drop_table("note_collection_membership")
