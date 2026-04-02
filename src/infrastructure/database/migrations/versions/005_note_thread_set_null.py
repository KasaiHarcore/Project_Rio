"""Change note.thread_id FK from CASCADE to SET NULL.

Revision ID: 005_note_thread_set_null
Revises: 004_add_langsmith_settings
Create Date: 2026-03-19

Changes:
- Alter note.thread_id foreign key from ON DELETE CASCADE to ON DELETE SET NULL
  so that notes persist independently when their originating thread is deleted.
"""

from alembic import op


revision = "005_note_thread_set_null"
down_revision = "004_add_langsmith_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("note_thread_id_fkey", "note", type_="foreignkey")
    op.create_foreign_key(
        "note_thread_id_fkey",
        "note",
        "thread",
        ["thread_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("note_thread_id_fkey", "note", type_="foreignkey")
    op.create_foreign_key(
        "note_thread_id_fkey",
        "note",
        "thread",
        ["thread_id"],
        ["id"],
        ondelete="CASCADE",
    )
