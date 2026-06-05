"""F-1: add audit triggers via postgres_fdw

Revision ID: 169975650e40
Revises: f4773a0c2f0d
Create Date: ...

"""
import os
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '169975650e40'
down_revision: Union[str, Sequence[str], None] = 'f4773a0c2f0d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ──────────────────────────────────────
    # 1) postgres_fdw 확장 활성화
    # ──────────────────────────────────────
    op.execute("CREATE EXTENSION IF NOT EXISTS postgres_fdw")

    # ──────────────────────────────────────
    # 2) 외부 서버 등록 (db_audit 컨테이너)
    # ──────────────────────────────────────
    op.execute("""
        CREATE SERVER IF NOT EXISTS audit_server
            FOREIGN DATA WRAPPER postgres_fdw
            OPTIONS (host 'db_audit', port '5432', dbname 'heartbeat_audit')
    """)

    # ──────────────────────────────────────
    # 3) User Mapping — DROP/CREATE 각각 별도 호출
    # ──────────────────────────────────────
    password = os.environ.get("DB_AUDIT_WRITER_PASSWORD")
    if not password:
        raise RuntimeError(
            "DB_AUDIT_WRITER_PASSWORD 환경변수가 필요합니다. "
            "docker-compose.yml의 api 서비스 environment 확인."
        )
    
    op.execute("DROP USER MAPPING IF EXISTS FOR heartbeat SERVER audit_server")
    op.execute(f"""
        CREATE USER MAPPING FOR heartbeat
            SERVER audit_server
            OPTIONS (user 'audit_writer', password '{password}')
    """)

    # ──────────────────────────────────────
    # 4) Foreign Table (db_audit.audit_logs_sensitive 가상 통로)
    # ──────────────────────────────────────
    op.execute("""
        CREATE FOREIGN TABLE IF NOT EXISTS audit_logs_sensitive_remote (
            user_id       UUID,
            action        VARCHAR(50),
            resource_type VARCHAR(50),
            resource_id   UUID
        ) SERVER audit_server
          OPTIONS (table_name 'audit_logs_sensitive')
    """)

    # ──────────────────────────────────────
    # 5) 트리거 함수 (4개 테이블 공유)
    #    함수 본문 안의 세미콜론은 dollar-quoted($$) 안이라 단일 statement로 인식됨 → OK
    # ──────────────────────────────────────
    op.execute("""
        CREATE OR REPLACE FUNCTION log_to_audit_sensitive()
        RETURNS TRIGGER
        LANGUAGE plpgsql
        SECURITY DEFINER
        AS $$
        BEGIN
            INSERT INTO audit_logs_sensitive_remote (
                user_id, action, resource_type, resource_id
            ) VALUES (
                NEW.user_id,
                'CREATE',
                CASE TG_TABLE_NAME
                    WHEN 'classifications'     THEN 'CLASSIFICATION'
                    WHEN 'counseling_sessions' THEN 'COUNSELING_SESSION'
                    WHEN 'summaries'           THEN 'SUMMARY'
                    WHEN 'crisis_events'       THEN 'CRISIS_EVENT'
                    ELSE upper(TG_TABLE_NAME)
                END,
                NEW.id
            );
            RETURN NEW;
        END;
        $$
    """)

    # ──────────────────────────────────────
    # 6) 트리거 4개 — DROP/CREATE 각각 별도 호출
    # ──────────────────────────────────────
    for table in ['classifications', 'counseling_sessions', 'summaries', 'crisis_events']:
        op.execute(f"DROP TRIGGER IF EXISTS trg_audit_{table} ON {table}")
        op.execute(f"""
            CREATE TRIGGER trg_audit_{table}
                AFTER INSERT ON {table}
                FOR EACH ROW EXECUTE FUNCTION log_to_audit_sensitive()
        """)


def downgrade() -> None:
    # upgrade의 역순으로 정리
    for table in ['crisis_events', 'summaries', 'counseling_sessions', 'classifications']:
        op.execute(f"DROP TRIGGER IF EXISTS trg_audit_{table} ON {table}")
    
    op.execute("DROP FUNCTION IF EXISTS log_to_audit_sensitive()")
    op.execute("DROP FOREIGN TABLE IF EXISTS audit_logs_sensitive_remote")
    op.execute("DROP USER MAPPING IF EXISTS FOR heartbeat SERVER audit_server")
    op.execute("DROP SERVER IF EXISTS audit_server")
    # postgres_fdw 확장은 다른 곳에서 쓸 수 있으니 안 지움