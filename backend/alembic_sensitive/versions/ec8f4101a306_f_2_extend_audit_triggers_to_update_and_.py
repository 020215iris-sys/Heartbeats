"""F-2: extend audit triggers to UPDATE and DELETE

Revision ID: ec8f4101a306
Revises: 169975650e40
Create Date: 2026-06-04 01:49:32.855834

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ec8f4101a306'
down_revision: Union[str, Sequence[str], None] = '169975650e40'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ──────────────────────────────────────
    # F-2: 기존 INSERT-only 트리거를 INSERT/UPDATE/DELETE 통합으로 확장
    # ──────────────────────────────────────
    
    # 1) 기존 INSERT-only 트리거 제거
    for table in ['classifications', 'counseling_sessions', 'summaries', 'crisis_events']:
        op.execute(f"DROP TRIGGER IF EXISTS trg_audit_{table} ON {table}")
    
    # 2) 함수 통합 — TG_OP 분기로 INSERT/UPDATE/DELETE 모두 처리
    op.execute("""
        CREATE OR REPLACE FUNCTION log_to_audit_sensitive()
        RETURNS TRIGGER
        LANGUAGE plpgsql
        SECURITY DEFINER
        AS $$
        DECLARE
            v_action       VARCHAR(50);
            v_user_id      UUID;
            v_resource_id  UUID;
        BEGIN
            -- TG_OP은 PostgreSQL이 트리거 발동 시 자동 채우는 변수
            -- 가능한 값: 'INSERT', 'UPDATE', 'DELETE', 'TRUNCATE'
            IF TG_OP = 'INSERT' THEN
                v_action      := 'CREATE';
                v_user_id     := NEW.user_id;
                v_resource_id := NEW.id;
            ELSIF TG_OP = 'UPDATE' THEN
                v_action      := 'UPDATE';
                v_user_id     := NEW.user_id;
                v_resource_id := NEW.id;
            ELSIF TG_OP = 'DELETE' THEN
                -- DELETE는 NEW가 없음. OLD 값만 존재
                v_action      := 'DELETE';
                v_user_id     := OLD.user_id;
                v_resource_id := OLD.id;
            END IF;

            INSERT INTO audit_logs_sensitive_remote (
                user_id, action, resource_type, resource_id
            ) VALUES (
                v_user_id,
                v_action,
                CASE TG_TABLE_NAME
                    WHEN 'classifications'     THEN 'CLASSIFICATION'
                    WHEN 'counseling_sessions' THEN 'COUNSELING_SESSION'
                    WHEN 'summaries'           THEN 'SUMMARY'
                    WHEN 'crisis_events'       THEN 'CRISIS_EVENT'
                    ELSE upper(TG_TABLE_NAME)
                END,
                v_resource_id
            );

            -- PostgreSQL 트리거 반환 규칙: INSERT/UPDATE는 NEW, DELETE는 OLD
            RETURN CASE TG_OP WHEN 'DELETE' THEN OLD ELSE NEW END;
        END;
        $$
    """)

    # 3) 트리거 4개 재부착 — INSERT/UPDATE/DELETE 모두 잡음
    for table in ['classifications', 'counseling_sessions', 'summaries', 'crisis_events']:
        op.execute(f"""
            CREATE TRIGGER trg_audit_{table}
                AFTER INSERT OR UPDATE OR DELETE ON {table}
                FOR EACH ROW EXECUTE FUNCTION log_to_audit_sensitive()
        """)
    pass


def downgrade() -> None:
    # F-1 상태로 복원 — 트리거를 INSERT-only 버전으로 되돌림
    
    # 1) 트리거 제거
    for table in ['classifications', 'counseling_sessions', 'summaries', 'crisis_events']:
        op.execute(f"DROP TRIGGER IF EXISTS trg_audit_{table} ON {table}")
    
    # 2) 함수를 F-1 버전(INSERT만)으로 복원
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
    
    # 3) 트리거 INSERT-only 버전으로 복원
    for table in ['classifications', 'counseling_sessions', 'summaries', 'crisis_events']:
        op.execute(f"""
            CREATE TRIGGER trg_audit_{table}
                AFTER INSERT ON {table}
                FOR EACH ROW EXECUTE FUNCTION log_to_audit_sensitive()
        """)
    pass
