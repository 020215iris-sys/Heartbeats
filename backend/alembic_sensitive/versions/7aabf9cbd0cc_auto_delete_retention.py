"""auto delete retention

Revision ID: 7aabf9cbd0cc
Revises: 3cece2dcf2cc
Create Date: 2026-06-14 07:44:10.626549

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '7aabf9cbd0cc'
down_revision: Union[str, Sequence[str], None] = '3cece2dcf2cc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    자동삭제 정책 도입:
    1) summaries.deleted_at 추가 (1년 정책 soft delete용)
    2) classification_results.deleted_at 추가 (parent classifications와 동기)
    3) counseling_sessions.user_id 익명화 대비 (1년 후 NULL로 SET 가능하도록 NOT NULL 해제)
    """
    # 1) summaries.deleted_at 추가
    op.add_column(
        'summaries',
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )

    # 2) classification_results.deleted_at 추가
    op.add_column(
        'classification_results',
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )

    # 3) counseling_sessions.user_id 익명화 대비
    #    1년 후 익명화 태스크가 user_id를 NULL로 SET 가능하도록 NOT NULL 해제.
    #    classification_id는 이미 nullable=True라 변경 불필요.
    op.alter_column(
        'counseling_sessions',
        'user_id',
        existing_type=UUID(as_uuid=True),
        existing_nullable=False,
        nullable=True,
    )


def downgrade() -> None:
    """
    역순으로 복구.

    ⚠️ user_id가 NULL인 행이 이미 있으면 NOT NULL 복원이 실패함.
    그런 경우 익명화된 행을 모두 처리(hard delete 또는 dummy uuid 채우기)해야 함.
    """
    op.alter_column(
        'counseling_sessions',
        'user_id',
        existing_type=UUID(as_uuid=True),
        existing_nullable=True,
        nullable=False,
    )
    op.drop_column('classification_results', 'deleted_at')
    op.drop_column('summaries', 'deleted_at')