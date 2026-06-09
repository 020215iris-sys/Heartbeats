"""F-3: capture client ip in audit triggers

Revision ID: 6700a48b527b
Revises: cf940627711c
Create Date: 2026-06-09 00:32:54.022039

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6700a48b527b'
down_revision: Union[str, Sequence[str], None] = 'cf940627711c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    F-3: 외래 테이블에 ip_address 컬럼 추가 + 트리거 함수가
    세션 변수 app.client_ip를 읽어 audit 로그에 IP 기록하도록 확장.

    백엔드 FastAPI middleware가 매 요청마다 다음 SQL을 실행해야 동작:
        SET app.client_ip = '<request.client.host>'
    """

    # ──────────────────────────────────────────
    # 1) 외래 테이블에 ip_address 컬럼 추가
    # ──────────────────────────────────────────
    # audit DB의 실제 테이블(audit_logs_sensitive)은 이미 ip_address INET 컬럼 보유.
    # 외래 테이블에 같은 컬럼을 노출시켜야 트리거가 그 컬럼으로 INSERT 가능.
    op.execute("""
        ALTER FOREIGN TABLE audit_logs_sensitive_remote
            ADD COLUMN ip_address INET
    """)

    # ──────────────────────────────────────────
    # 2) 트리거 함수 갱신 — session variable에서 IP 읽기
    # ──────────────────────────────────────────
    # current_setting의 두 번째 인자 true = missing_ok
    #   → app.client_ip가 SET되지 않은 환경에서도 에러 없이 빈 문자열 반환
    # NULLIF(x, '')로 빈 문자열을 NULL로 변환한 뒤 inet 캐스팅
    #   → 마이그레이션 자체, psql 직접 INSERT 등 middleware 없는 케이스에서
    #     안전하게 NULL로 떨어짐 (캐스팅 에러 방지)
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
            v_ip           INET;
        BEGIN
            -- 세션 변수에서 클라이언트 IP 추출 (없으면 NULL)
            v_ip := NULLIF(current_setting('app.client_ip', true), '')::inet;

            IF TG_OP = 'INSERT' THEN
                v_action      := 'CREATE';
                v_user_id     := NEW.user_id;
                v_resource_id := NEW.id;
            ELSIF TG_OP = 'UPDATE' THEN
                v_action      := 'UPDATE';
                v_user_id     := NEW.user_id;
                v_resource_id := NEW.id;
            ELSIF TG_OP = 'DELETE' THEN
                v_action      := 'DELETE';
                v_user_id     := OLD.user_id;
                v_resource_id := OLD.id;
            END IF;

            INSERT INTO audit_logs_sensitive_remote (
                user_id, action, resource_type, resource_id, ip_address
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
                v_resource_id,
                v_ip
            );

            RETURN CASE TG_OP WHEN 'DELETE' THEN OLD ELSE NEW END;
        END;
        $$
    """)


def downgrade() -> None:
    """
    F-3 롤백: 트리거 함수를 F-2 버전(ip 없는 버전)으로 복원 +
    외래 테이블에서 ip_address 컬럼 제거.

    순서 중요: 함수 먼저 복원(새 컬럼 참조 중단), 그 다음 컬럼 제거.
    역순으로 하면 함수가 살아있는 동안 컬럼이 없어져서 INSERT 실패.
    """

    # ──────────────────────────────────────────
    # 1) 트리거 함수를 F-2 버전으로 복원
    # ──────────────────────────────────────────
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
            IF TG_OP = 'INSERT' THEN
                v_action      := 'CREATE';
                v_user_id     := NEW.user_id;
                v_resource_id := NEW.id;
            ELSIF TG_OP = 'UPDATE' THEN
                v_action      := 'UPDATE';
                v_user_id     := NEW.user_id;
                v_resource_id := NEW.id;
            ELSIF TG_OP = 'DELETE' THEN
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

            RETURN CASE TG_OP WHEN 'DELETE' THEN OLD ELSE NEW END;
        END;
        $$
    """)

    # ──────────────────────────────────────────
    # 2) 외래 테이블에서 ip_address 컬럼 제거
    # ──────────────────────────────────────────
    op.execute("""
        ALTER FOREIGN TABLE audit_logs_sensitive_remote
            DROP COLUMN ip_address
    """)