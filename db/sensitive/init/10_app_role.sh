#!/bin/bash
# 10_app_role.sh
# sensitive DB · 백엔드 트래픽용 제한 롤(sensitive_app) 생성
#
# 권한 분리 원칙 (옵션 B):
#   - SELECT/INSERT/UPDATE/DELETE만 부여
#   - DDL/TRUNCATE/DISABLE TRIGGER 미부여 → 자동 차단
#
# 주의: F-1/F-2 audit 트리거 함수에 대한 GRANT EXECUTE는 여기서 부여 안 함.
#   이유 1) init 시점엔 트리거 함수가 아직 없음 (alembic이 나중에 생성)
#   이유 2) 함수가 SECURITY DEFINER라 호출자 권한 불필요 (함수 OWNER 권한으로 실행)
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- 1) 애플리케이션 전용 제한 계정 생성
    CREATE ROLE sensitive_app LOGIN PASSWORD '${DB_SENSITIVE_APP_PASSWORD}';

    -- 2) DB 접속 권한 + 스키마 사용 권한
    GRANT CONNECT ON DATABASE ${POSTGRES_DB} TO sensitive_app;
    GRANT USAGE   ON SCHEMA public           TO sensitive_app;

    -- 3) 기존 테이블 CRUD 권한
    GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES    IN SCHEMA public TO sensitive_app;

    -- 4) 시퀀스 사용 권한 (UUID PK 위주라 거의 안 쓰이지만 미래 대비)
    GRANT USAGE, SELECT                  ON ALL SEQUENCES IN SCHEMA public TO sensitive_app;

    -- 5) 미래 테이블에 자동 권한 부여
    --    alembic이 새 테이블 만들면 자동으로 sensitive_app도 권한 받음
    ALTER DEFAULT PRIVILEGES FOR ROLE heartbeat IN SCHEMA public
        GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES    TO sensitive_app;
    ALTER DEFAULT PRIVILEGES FOR ROLE heartbeat IN SCHEMA public
        GRANT USAGE, SELECT                  ON SEQUENCES TO sensitive_app;
EOSQL