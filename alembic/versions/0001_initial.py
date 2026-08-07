"""initial schema

Revision ID: 0001_initial
Revises: 
Create Date: 2026-08-07 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # users
    op.create_table(
        'user',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('username', sa.String(), nullable=False, unique=True),
        sa.Column('email', sa.String(), nullable=True, unique=True),
        sa.Column('password_hash', sa.String(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False),
    )

    # refresh_tokens
    op.create_table(
        'refreshtoken',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('token_hash', sa.String(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('expires_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('revoked', sa.Boolean(), nullable=False, server_default=sa.text('false')),
    )

    # words
    op.create_table(
        'word',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('german', sa.String(), nullable=False),
        sa.Column('english', sa.String(), nullable=True),
        sa.Column('part_of_speech', sa.String(), nullable=True),
        sa.Column('source', sa.String(), nullable=True),
        sa.Column('tags', postgresql.JSONB(), nullable=True),
        sa.Column('total_practices', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('correct_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_practiced_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('interval_seconds', sa.Integer(), nullable=True),
        sa.Column('repetitions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('ease_factor', sa.Float(), nullable=False, server_default='2.5'),
        sa.Column('next_due', sa.TIMESTAMP(), nullable=True),
        sa.Column('last_reviewed_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('user.id'), nullable=False),
    )

    # phrases
    op.create_table(
        'phrase',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('german', sa.String(), nullable=False),
        sa.Column('english', sa.String(), nullable=True),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('tags', postgresql.JSONB(), nullable=True),
        sa.Column('total_practices', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('correct_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_practiced_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('interval_seconds', sa.Integer(), nullable=True),
        sa.Column('repetitions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('ease_factor', sa.Float(), nullable=False, server_default='2.5'),
        sa.Column('next_due', sa.TIMESTAMP(), nullable=True),
        sa.Column('last_reviewed_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('user.id'), nullable=False),
    )

    # sentence_templates
    op.create_table(
        'sentencetemplate',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('template_text', sa.String(), nullable=False),
        sa.Column('translation_hint', sa.String(), nullable=True),
        sa.Column('examples_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('tags', postgresql.JSONB(), nullable=True),
        sa.Column('interval_seconds', sa.Integer(), nullable=True),
        sa.Column('repetitions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('ease_factor', sa.Float(), nullable=False, server_default='2.5'),
        sa.Column('next_due', sa.TIMESTAMP(), nullable=True),
        sa.Column('last_reviewed_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('user.id'), nullable=False),
    )

    # practice_events
    op.create_table(
        'practiceevent',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('item_type', sa.String(), nullable=False),
        sa.Column('item_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('attempted_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('outcome', sa.String(), nullable=False),
        sa.Column('details', postgresql.JSONB(), nullable=True),
    )

    # indexes
    op.create_index('ix_word_owner_next_due', 'word', ['owner_id', 'next_due'])
    op.create_index('ix_phrase_owner_next_due', 'phrase', ['owner_id', 'next_due'])
    op.create_index('ix_template_owner_next_due', 'sentencetemplate', ['owner_id', 'next_due'])


def downgrade():
    op.drop_index('ix_template_owner_next_due', table_name='sentencetemplate')
    op.drop_index('ix_phrase_owner_next_due', table_name='phrase')
    op.drop_index('ix_word_owner_next_due', table_name='word')
    op.drop_table('practiceevent')
    op.drop_table('sentencetemplate')
    op.drop_table('phrase')
    op.drop_table('word')
    op.drop_table('refreshtoken')
    op.drop_table('user')
