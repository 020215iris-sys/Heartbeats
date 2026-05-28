#!/bin/bash
# 04_roles.sh
# audit DB · 애플리케이션 전용 제한 롤(audit_writer) 생성
# INSERT-only 원칙: 로그 추가/조회만, 수정/삭제 불가
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- 애플리케이션 전용 제한 계정
    CREATE ROLE audit_writer LOGIN PASSWORD '${DB_AUDIT_WRITER_PASSWORD}';

    -- 접속 + 스키마 사용 권한
    GRANT CONNECT ON DATABASE ${POSTGRES_DB} TO audit_writer;
    GRANT USAGE   ON SCHEMA public           TO audit_writer;

    -- INSERT, SELECT만 (UPDATE/DELETE/TRUNCATE 미부여 = 변조 차단)
    GRANT INSERT, SELECT ON audit_logs_general   TO audit_writer;
    GRANT INSERT, SELECT ON audit_logs_sensitive TO audit_writer;

    -- bigserial id 시퀀스 사용 권한 (INSERT 시 필요)
    GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO audit_writer;
EOSQL