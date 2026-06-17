"""add preserved messages to crisis events

Revision ID: d4d62cf83ff8
Revises: a149c576abcd
Create Date: 2026-06-17 06:09:26.447993

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4d62cf83ff8'
down_revision: Union[str, Sequence[str], None] = 'a149c576abcd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 위기 발화 앞뒤 N개 메시지 박제(W3 헬퍼로 JSON 배열을 AES-256-GCM 암호화).
    # 90일 자동삭제와 무관하게 영구 보존하기 위해 crisis_events 자체에 freeze.
    op.add_column('crisis_events',
        sa.Column('preserved_messages_encrypted', sa.LargeBinary(), nullable=True))
    op.add_column('crisis_events',
        sa.Column('preserved_messages_key_id', sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column('crisis_events', 'preserved_messages_key_id')
    op.drop_column('crisis_events', 'preserved_messages_encrypted')
