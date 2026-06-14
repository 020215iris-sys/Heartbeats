"""summaries encrypt w2

Revision ID: 3cece2dcf2cc
Revises: 8c5d3174fa3e
Create Date: 2026-06-12 12:36:06.970102

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3cece2dcf2cc'
down_revision: Union[str, Sequence[str], None] = '8c5d3174fa3e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    1) 새 컬럼 4개 추가
    2) 기존 평문 → AES 암호화해서 백필
    3) 옛 TEXT 컬럼 제거
    """
    # crypto 헬퍼는 함수 안에서 import (모듈 로드 시점 의존 최소화)
    from core.crypto import encrypt_content

    # ───── 1) 새 컬럼 추가 ─────
    op.add_column(
        'summaries',
        sa.Column('main_complaint_encrypted', sa.LargeBinary(), nullable=True),
    )
    op.add_column(
        'summaries',
        sa.Column('main_complaint_key_id', sa.String(50), nullable=True),
    )
    op.add_column(
        'summaries',
        sa.Column('next_session_notes_encrypted', sa.LargeBinary(), nullable=True),
    )
    op.add_column(
        'summaries',
        sa.Column('next_session_notes_key_id', sa.String(50), nullable=True),
    )

    # ───── 2) 기존 평문 행 백필 ─────
    bind = op.get_bind()
    rows = bind.execute(sa.text(
        "SELECT id, main_complaint, next_session_notes FROM summaries"
    )).fetchall()

    update_sql = sa.text("""
        UPDATE summaries SET
            main_complaint_encrypted = :mc_bytes,
            main_complaint_key_id = :mc_kid,
            next_session_notes_encrypted = :nsn_bytes,
            next_session_notes_key_id = :nsn_kid
        WHERE id = :id
    """)

    for row in rows:
        mc_bytes, mc_kid = encrypt_content(row.main_complaint or "")
        nsn_bytes, nsn_kid = encrypt_content(row.next_session_notes or "")
        bind.execute(update_sql, {
            "mc_bytes": mc_bytes,
            "mc_kid": mc_kid,
            "nsn_bytes": nsn_bytes,
            "nsn_kid": nsn_kid,
            "id": row.id,
        })

    # ───── 3) 옛 컬럼 제거 ─────
    op.drop_column('summaries', 'main_complaint')
    op.drop_column('summaries', 'next_session_notes')


def downgrade() -> None:
    """
    역순으로 옛 컬럼 복원 → 평문 디코딩 백필 → 새 컬럼 제거.

    ⚠️ AES-256-GCM 복호화는 무손실이라 평문 그대로 복원되지만,
    크립토 키가 사라지면 영구히 복원 불가. 운영에서 함부로 돌리지 말 것.
    """
    from core.crypto import decrypt_content

    op.add_column('summaries', sa.Column('main_complaint', sa.Text(), nullable=True))
    op.add_column('summaries', sa.Column('next_session_notes', sa.Text(), nullable=True))

    bind = op.get_bind()
    rows = bind.execute(sa.text(
        "SELECT id, main_complaint_encrypted, main_complaint_key_id, "
        "next_session_notes_encrypted, next_session_notes_key_id FROM summaries"
    )).fetchall()

    update_sql = sa.text("""
        UPDATE summaries SET
            main_complaint = :mc,
            next_session_notes = :nsn
        WHERE id = :id
    """)

    for row in rows:
        mc = decrypt_content(row.main_complaint_encrypted, row.main_complaint_key_id) \
            if row.main_complaint_encrypted is not None else None
        nsn = decrypt_content(row.next_session_notes_encrypted, row.next_session_notes_key_id) \
            if row.next_session_notes_encrypted is not None else None
        bind.execute(update_sql, {"mc": mc, "nsn": nsn, "id": row.id})

    op.drop_column('summaries', 'next_session_notes_key_id')
    op.drop_column('summaries', 'next_session_notes_encrypted')
    op.drop_column('summaries', 'main_complaint_key_id')
    op.drop_column('summaries', 'main_complaint_encrypted')