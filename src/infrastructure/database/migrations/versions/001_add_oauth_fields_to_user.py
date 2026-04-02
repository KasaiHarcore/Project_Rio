"""Add OAuth fields to user model.

Revision ID: 001_add_oauth_fields
Revises:
Create Date: 2026-03-08

Changes:
- Add auth_provider enum column (default 'local')
- Add oauth_id column (nullable)
- Add avatar_url column (nullable)
- Make hashed_password nullable (for OAuth users)
"""

from alembic import op
import sqlalchemy as sa

revision = "001_add_oauth_fields"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create the AuthProvider enum type
    auth_provider_enum = sa.Enum("local", "google", "github", name="authprovider")
    auth_provider_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "user",
        sa.Column(
            "auth_provider",
            auth_provider_enum,
            nullable=False,
            server_default="local",
        ),
    )
    op.add_column(
        "user",
        sa.Column("oauth_id", sa.String(255), nullable=True),
    )
    op.add_column(
        "user",
        sa.Column("avatar_url", sa.String(500), nullable=True),
    )

    # Make hashed_password nullable for OAuth users
    op.alter_column(
        "user",
        "hashed_password",
        existing_type=sa.String(255),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "user",
        "hashed_password",
        existing_type=sa.String(255),
        nullable=False,
    )
    op.drop_column("user", "avatar_url")
    op.drop_column("user", "oauth_id")
    op.drop_column("user", "auth_provider")

    sa.Enum(name="authprovider").drop(op.get_bind(), checkfirst=True)
