"""Record password reset fields already included in the initial schema.

Revision ID: 0002_auth_reset_tokens
Revises: 0001_initial

The reset-token columns were included in ``0001_initial``. This revision is
kept in the migration chain for databases that already reference it, but
must not attempt to add or remove those columns a second time.
"""

revision = "0002_auth_reset_tokens"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
