"""Add LangSmith settings and change guardrail defaults.

Revision ID: 004_add_langsmith_settings
Revises: 003_note_collection_m2m
Create Date: 2026-03-18

Changes:
- Add encrypted_langsmith_key column to user_settings
- Add enable_langsmith_tracing column (default false)
- Add langsmith_project column
- Change enable_input_guardrail default to false
- Change enable_output_guardrail default to false
"""

from alembic import op
import sqlalchemy as sa


revision = "004_add_langsmith_settings"
down_revision = "003_note_collection_m2m"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_settings",
        sa.Column("encrypted_langsmith_key", sa.Text(), nullable=True),
    )
    op.add_column(
        "user_settings",
        sa.Column(
            "enable_langsmith_tracing",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    op.add_column(
        "user_settings",
        sa.Column("langsmith_project", sa.String(200), nullable=True),
    )

    # Change guardrail defaults to false for new rows
    op.alter_column(
        "user_settings",
        "enable_input_guardrail",
        server_default="false",
    )
    op.alter_column(
        "user_settings",
        "enable_output_guardrail",
        server_default="false",
    )


def downgrade() -> None:
    op.drop_column("user_settings", "langsmith_project")
    op.drop_column("user_settings", "enable_langsmith_tracing")
    op.drop_column("user_settings", "encrypted_langsmith_key")

    op.alter_column(
        "user_settings",
        "enable_input_guardrail",
        server_default="true",
    )
    op.alter_column(
        "user_settings",
        "enable_output_guardrail",
        server_default="true",
    )
