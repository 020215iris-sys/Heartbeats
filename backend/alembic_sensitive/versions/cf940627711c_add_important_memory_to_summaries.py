"""add important_memory to summaries

Revision ID: cf940627711c
Revises: ec8f4101a306
Create Date: 2026-06-08 12:16:11.413194

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql



# revision identifiers, used by Alembic.
revision: str = 'cf940627711c'
down_revision: Union[str, Sequence[str], None] = 'ec8f4101a306'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    op.add_column(
        "summaries",
        sa.Column(
            "important_memory",
            postgresql.JSONB(),
            nullable=True
        )
    )


def downgrade():
    op.drop_column(
        "summaries",
        "important_memory"
    )
