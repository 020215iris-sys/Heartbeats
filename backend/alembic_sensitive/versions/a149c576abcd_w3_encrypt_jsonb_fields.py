"""w3_encrypt_jsonb_fields

Revision ID: a149c576abcd
Revises: 7aabf9cbd0cc
Create Date: 2026-06-15 11:51:43.857197

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a149c576abcd'
down_revision: Union[str, Sequence[str], None] = '7aabf9cbd0cc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # summaries
    op.add_column('summaries',
        sa.Column('core_topics_encrypted', sa.LargeBinary(), nullable=True))
    op.add_column('summaries',
        sa.Column('core_topics_key_id', sa.String(length=50), nullable=True))
    op.add_column('summaries',
        sa.Column('important_memory_encrypted', sa.LargeBinary(), nullable=True))
    op.add_column('summaries',
        sa.Column('important_memory_key_id', sa.String(length=50), nullable=True))

    # classifications
    op.add_column('classifications',
        sa.Column('compound_flags_encrypted', sa.LargeBinary(), nullable=True))
    op.add_column('classifications',
        sa.Column('compound_flags_key_id', sa.String(length=50), nullable=True))

    # classification_results
    op.add_column('classification_results',
        sa.Column('responses_encrypted', sa.LargeBinary(), nullable=True))
    op.add_column('classification_results',
        sa.Column('responses_key_id', sa.String(length=50), nullable=True))

    # crisis_events
    op.add_column('crisis_events',
        sa.Column('action_taken_encrypted', sa.LargeBinary(), nullable=True))
    op.add_column('crisis_events',
        sa.Column('action_taken_key_id', sa.String(length=50), nullable=True))


def downgrade() -> None:
    # 역순 DROP. 옛 평문 컬럼은 손대지 않음.
    op.drop_column('crisis_events', 'action_taken_key_id')
    op.drop_column('crisis_events', 'action_taken_encrypted')

    op.drop_column('classification_results', 'responses_key_id')
    op.drop_column('classification_results', 'responses_encrypted')

    op.drop_column('classifications', 'compound_flags_key_id')
    op.drop_column('classifications', 'compound_flags_encrypted')

    op.drop_column('summaries', 'important_memory_key_id')
    op.drop_column('summaries', 'important_memory_encrypted')
    op.drop_column('summaries', 'core_topics_key_id')
    op.drop_column('summaries', 'core_topics_encrypted')