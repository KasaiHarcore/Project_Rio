"""add tool_name discriminator column to message table

Revision ID: 005_add_tool_message_fields
Revises: 004_add_message_metadata
Create Date: 2026-04-19

Tool results are now persisted as Message rows with role='tool'. The
``tool_name`` column gives the tree-view a cheap "what worker produced
this" lookup without having to parse the JSONB metadata or the content.
The MessageRole enum already includes the TOOL value (see
``src/models/message.py``), so no enum migration is needed.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '005_add_tool_message_fields'
down_revision: Union[str, None] = '004_add_message_metadata'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'message',
        sa.Column('tool_name', sa.String(length=64), nullable=True),
    )
    op.create_index('ix_message_tool_name', 'message', ['tool_name'])


def downgrade() -> None:
    op.drop_index('ix_message_tool_name', table_name='message')
    op.drop_column('message', 'tool_name')
