#!/bin/bash
# 05_app_role.sh
# general DB · 백엔드 트래픽용 제한 롤(general_app) 생성
#
# 권한 분리 원칙 (옵션 B):
#   - SELECT/INSERT/UPDATE/DELETE만 부여
#   - DDL(CREATE/DROP/ALTER)/TRUNCATE/DISABLE TRIGGER 미부여 → 자동 차단
#   - SQL injection 또는 코드 실수로 백엔드 계정이 탈취돼도
#     테이블 삭제·트리거 무력화는 불가능
#
# 적용 시점: 컨테이너 최초 기동 시 (빈 볼륨)
# 이미 운영 중인 환경에는 scripts/apply_option_b.sh로 별도 적용
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- 1) 애플리케이션 전용 제한 계정 생성
    --    LOGIN: 직접 접속 허용
    --    PASSWORD는 docker-compose가 환경변수로 주입 (.env의 DB_GENERAL_APP_PASSWORD)
    CREATE ROLE general_app LOGIN PASSWORD '${DB_GENERAL_APP_PASSWORD}';

    -- 2) DB 접속 권한 + 스키마 사용 권한
    --    CONNECT 없으면 접속 자체가 거부됨
    --    USAGE 없으면 스키마 안의 객체에 접근 불가
    GRANT CONNECT ON DATABASE ${POSTGRES_DB} TO general_app;
    GRANT USAGE   ON SCHEMA public           TO general_app;

    -- 3) 기존 테이블 CRUD 권한
    --    SELECT/INSERT/UPDATE/DELETE만 (TRUNCATE는 별도 권한이라 자동 차단)
    --    DDL은 OWNER만 가능하니 미부여로 자동 차단
    GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES    IN SCHEMA public TO general_app;

    -- 4) 시퀀스 사용 권한
    --    BIGSERIAL/SERIAL 컬럼에 INSERT 할 때 nextval()/currval() 호출에 필요
    GRANT USAGE, SELECT                  ON ALL SEQUENCES IN SCHEMA public TO general_app;

    -- 5) 미래 테이블에 자동 권한 부여
    --    alembic이 새 테이블 만들면(heartbeat 권한으로) 자동으로 general_app도 권한 받음
    --    이게 없으면 마이그레이션마다 수동 GRANT가 필요
    ALTER DEFAULT PRIVILEGES FOR ROLE heartbeat IN SCHEMA public
        GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES    TO general_app;
    ALTER DEFAULT PRIVILEGES FOR ROLE heartbeat IN SCHEMA public
        GRANT USAGE, SELECT                  ON SEQUENCES TO general_app;
EOSQL