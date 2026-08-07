"""add template practice aggregate fields

Revision ID: 0003_template_practice_fields
Revises: 0002_auth_reset_tokens
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_template_practice_fields"
down_revision = "0002_auth_reset_tokens"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "sentencetemplate",
        sa.Column("total_practices", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "sentencetemplate",
        sa.Column("correct_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "sentencetemplate",
        sa.Column("last_practiced_at", sa.TIMESTAMP(), nullable=True),
    )


def downgrade():
    op.drop_column("sentencetemplate", "last_practiced_at")
    op.drop_column("sentencetemplate", "correct_count")
    op.drop_column("sentencetemplate", "total_practices")
