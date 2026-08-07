"""add password reset fields

Revision ID: 0002_auth_reset_tokens
Revises: 0001_initial
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_auth_reset_tokens"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("user", sa.Column("reset_token_hash", sa.String(), nullable=True))
    op.add_column(
        "user",
        sa.Column("reset_token_expires_at", sa.TIMESTAMP(), nullable=True),
    )


def downgrade():
    op.drop_column("user", "reset_token_expires_at")
    op.drop_column("user", "reset_token_hash")
