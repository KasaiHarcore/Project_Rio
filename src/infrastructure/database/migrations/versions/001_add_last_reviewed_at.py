"""add last_reviewed_at to flashcard

Revision ID: 001_add_last_reviewed_at
Revises:
Create Date: 2026-04-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '001_add_last_reviewed_at'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'flashcard',
        sa.Column('last_reviewed_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('flashcard', 'last_reviewed_at')
