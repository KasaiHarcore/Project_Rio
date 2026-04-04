"""create audio_overview table

Revision ID: 002_create_audio_overview
Revises: 001_add_last_reviewed_at
Create Date: 2026-04-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002_create_audio_overview'
down_revision: Union[str, None] = '001_add_last_reviewed_at'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types
    audiostatus = postgresql.ENUM(
        'pending', 'generating', 'ready', 'failed',
        name='audiostatus',
        create_type=False,
    )
    audiostatus.create(op.get_bind(), checkfirst=True)

    audioformat = postgresql.ENUM(
        'summary', 'dialogue', 'lecture',
        name='audioformat',
        create_type=False,
    )
    audioformat.create(op.get_bind(), checkfirst=True)

    audiosourcetype = postgresql.ENUM(
        'notes', 'documents', 'flashcards',
        name='audiosourcetype',
        create_type=False,
    )
    audiosourcetype.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'audio_overview',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('source_ids', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column('source_type', sa.Enum('notes', 'documents', 'flashcards', name='audiosourcetype'), nullable=False),
        sa.Column('transcript', sa.Text, nullable=True),
        sa.Column('audio_path', sa.String(500), nullable=True),
        sa.Column('duration_seconds', sa.Integer, nullable=True),
        sa.Column('format', sa.Enum('summary', 'dialogue', 'lecture', name='audioformat'), nullable=False),
        sa.Column('status', sa.Enum('pending', 'generating', 'ready', 'failed', name='audiostatus'), nullable=False, server_default='pending'),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )

    op.create_index('ix_audio_overview_user_id', 'audio_overview', ['user_id'])
    op.create_index('ix_audio_overview_id', 'audio_overview', ['id'])
    op.create_index('ix_audio_overview_user_status', 'audio_overview', ['user_id', 'status'])


def downgrade() -> None:
    op.drop_index('ix_audio_overview_user_status', table_name='audio_overview')
    op.drop_index('ix_audio_overview_id', table_name='audio_overview')
    op.drop_index('ix_audio_overview_user_id', table_name='audio_overview')
    op.drop_table('audio_overview')

    op.execute('DROP TYPE IF EXISTS audiostatus')
    op.execute('DROP TYPE IF EXISTS audioformat')
    op.execute('DROP TYPE IF EXISTS audiosourcetype')
