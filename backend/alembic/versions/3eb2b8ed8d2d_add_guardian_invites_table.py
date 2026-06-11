"""add guardian_invites table

Revision ID: 3eb2b8ed8d2d
Revises: 914124ce1590
Create Date: 2026-06-11 07:00:16.168662

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '3eb2b8ed8d2d'
down_revision: Union[str, Sequence[str], None] = '914124ce1590'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    guardian_invites: 보호자 가입 게이트키퍼 + 영구 연결 매핑 (겸직 테이블).

    역할 1: status='pending' — 일회성 가입 인증 토큰 (8자리 숫자, 1시간 만료)
    역할 2: status='accepted' AND revoked_at IS NULL — 영구 연결 (대시보드 조회 권한)

    흐름:
      1) ward가 POST /guardian/invite → 코드 발급 (pending, expires=now+1h)
      2) ward가 보호자에게 코드 전달 (현재: 복사 / 향후: SMS 자동)
      3) 보호자가 /auth/signup에 invite_code 입력 → 가입 + 연결 (한 트랜잭션, 후속 PR)
    """
    op.create_table(
        "guardian_invites",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("code", sa.String(8), nullable=False, unique=True),
        sa.Column(
            "ward_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "guardian_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("attempt_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'accepted', 'expired', 'revoked')",
            name="guardian_invites_status_check",
        ),
        sa.CheckConstraint(
            "attempt_count >= 0",
            name="guardian_invites_attempt_count_nonneg",
        ),
        # code 형식 강제: 정확히 8자리 숫자만 (~ 는 PostgreSQL POSIX 정규식 매치)
        sa.CheckConstraint(
            "code ~ '^[0-9]{8}$'",
            name="guardian_invites_code_format",
        ),
    )

    # ward별 발급 이력 조회용
    op.create_index("idx_gi_ward_user_id", "guardian_invites", ["ward_user_id"])
    # 보호자가 자기 연결된 ward 목록 조회용
    op.create_index("idx_gi_guardian_user_id", "guardian_invites", ["guardian_user_id"])
    # 부분 인덱스: pending인 행만 인덱싱 → 만료 정리 배치 효율화 + 인덱스 크기 ↓
    op.execute("""
        CREATE INDEX idx_gi_expires_at_pending
            ON guardian_invites(expires_at)
            WHERE status = 'pending'
    """)


def downgrade() -> None:
    """역순으로 인덱스 → 테이블 제거. CHECK 제약과 FK는 DROP TABLE에 묻혀 사라짐."""
    op.execute("DROP INDEX IF EXISTS idx_gi_expires_at_pending")
    op.drop_index("idx_gi_guardian_user_id", table_name="guardian_invites")
    op.drop_index("idx_gi_ward_user_id", table_name="guardian_invites")
    op.drop_table("guardian_invites")