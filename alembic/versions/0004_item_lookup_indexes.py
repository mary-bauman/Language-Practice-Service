"""add item lookup indexes

Revision ID: 0004_item_lookup_indexes
Revises: 0003_template_practice_fields
"""

from alembic import op


revision = "0004_item_lookup_indexes"
down_revision = "0003_template_practice_fields"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "ix_word_owner_german",
        "word",
        ["owner_id", "german"],
    )
    op.create_index(
        "ix_phrase_owner_german",
        "phrase",
        ["owner_id", "german"],
    )
    op.create_index(
        "ix_word_tags_gin",
        "word",
        ["tags"],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_phrase_tags_gin",
        "phrase",
        ["tags"],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_sentencetemplate_tags_gin",
        "sentencetemplate",
        ["tags"],
        postgresql_using="gin",
    )


def downgrade():
    op.drop_index("ix_sentencetemplate_tags_gin", table_name="sentencetemplate")
    op.drop_index("ix_phrase_tags_gin", table_name="phrase")
    op.drop_index("ix_word_tags_gin", table_name="word")
    op.drop_index("ix_phrase_owner_german", table_name="phrase")
    op.drop_index("ix_word_owner_german", table_name="word")
