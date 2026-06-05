#!/bin/bash
# scripts/apply_option_b.sh
#
# 옵션 B (RBAC 권한 분리): 백엔드용 제한 권한 ROLE 추가
# - general DB:   general_app   (CRUD만, OWNER/SUPERUSER 아님)
# - sensitive DB: sensitive_app (CRUD만, OWNER/SUPERUSER 아님)
# - audit DB:     변경 없음 (audit_writer 이미 존재)
#
# 멱등(idempotent): 여러 번 실행해도 안전. ROLE이 있으면 비번만 갱신.
# 사용: bash scripts/apply_option_b.sh
# 사전: 프로젝트 루트 .env에 두 비번 추가 필요

set -e   # 에러 발생 시 즉시 중단

# ──────────────────────────────────────
# 1) .env 로드 — 컨테이너 안에서가 아니라 호스트에서 실행되므로
#    프로젝트 루트의 .env를 직접 읽어야 함
# ──────────────────────────────────────
if [ -f .env ]; then
    set -a              # 자동 export: 이후 source 한 변수는 자동으로 환경에 export
    . ./.env
    set +a
fi

# ──────────────────────────────────────
# 2) 필수 환경변수 검증
#    ${VAR:?에러메시지} 패턴: VAR이 없거나 빈 값이면 에러 출력 후 종료
# ──────────────────────────────────────
: "${DB_GENERAL_APP_PASSWORD:?DB_GENERAL_APP_PASSWORD가 .env에 없음}"
: "${DB_SENSITIVE_APP_PASSWORD:?DB_SENSITIVE_APP_PASSWORD가 .env에 없음}"

echo "🔄 옵션 B 적용 시작..."

# ──────────────────────────────────────
# 3) general DB에 general_app 생성
# ──────────────────────────────────────
echo ""
echo "  → general DB (5432) ..."
# <<-'EOSQL': quoted heredoc → 쉘 변수 확장 안 함 (psql에 그대로 전달)
# psql -v app_password=...: psql 변수로 비번 전달 (:'app_password'로 참조)
# -v ON_ERROR_STOP=1: SQL 중 하나라도 실패하면 즉시 중단 (부분 적용 방지)
docker exec -i heartbeat_db_general \
    psql -U heartbeat -d heartbeat_general \
    -v ON_ERROR_STOP=1 \
    -v app_password="$DB_GENERAL_APP_PASSWORD" <<-'EOSQL'

    -- ROLE 생성 (이미 있으면 무시)
    -- DO $$ ... $$: 익명 PL/pgSQL 블록. PostgreSQL의 절차적 처리.
    -- EXCEPTION WHEN duplicate_object: ROLE이 이미 있으면 에러 잡고 통과 → 멱등성 확보
    DO $$ BEGIN
        CREATE ROLE general_app LOGIN;
    EXCEPTION WHEN duplicate_object THEN
        RAISE NOTICE 'general_app 이미 존재, 비번만 갱신';
    END $$;

    -- 비번은 항상 갱신 (CREATE에서 비번 못 줬어도 여기서 설정됨)
    -- :'app_password'는 psql이 안전하게 따옴표로 감싸서 SQL 인젝션 방지
    ALTER ROLE general_app WITH PASSWORD :'app_password';

    -- DB 접속 권한
    GRANT CONNECT ON DATABASE heartbeat_general TO general_app;
    -- 스키마 사용 권한 (이게 없으면 안의 테이블 자체에 접근 불가)
    GRANT USAGE ON SCHEMA public TO general_app;

    -- 기존 테이블/시퀀스에 CRUD 권한
    -- DDL(CREATE/DROP/ALTER), TRUNCATE는 부여하지 않음 → 자동 차단
    GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES    IN SCHEMA public TO general_app;
    GRANT USAGE, SELECT                ON ALL SEQUENCES IN SCHEMA public TO general_app;

    -- 미래 테이블에도 자동 권한 부여 (heartbeat가 만드는 경우만)
    -- alembic 마이그레이션으로 새 테이블 생기면 자동으로 general_app도 권한 받음
    ALTER DEFAULT PRIVILEGES FOR ROLE heartbeat IN SCHEMA public
        GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES    TO general_app;
    ALTER DEFAULT PRIVILEGES FOR ROLE heartbeat IN SCHEMA public
        GRANT USAGE, SELECT                  ON SEQUENCES TO general_app;

    -- 결과 확인 — rolsuper=false, rolcanlogin=true가 정상
    SELECT rolname, rolcanlogin, rolsuper, rolcreatedb
    FROM pg_roles WHERE rolname = 'general_app';
EOSQL

# ──────────────────────────────────────
# 4) sensitive DB에 sensitive_app 생성 (구조 동일)
# ──────────────────────────────────────
echo ""
echo "  → sensitive DB (5433) ..."
docker exec -i heartbeat_db_sensitive \
    psql -U heartbeat -d heartbeat_sensitive \
    -v ON_ERROR_STOP=1 \
    -v app_password="$DB_SENSITIVE_APP_PASSWORD" <<-'EOSQL'

    DO $$ BEGIN
        CREATE ROLE sensitive_app LOGIN;
    EXCEPTION WHEN duplicate_object THEN
        RAISE NOTICE 'sensitive_app 이미 존재, 비번만 갱신';
    END $$;

    ALTER ROLE sensitive_app WITH PASSWORD :'app_password';

    GRANT CONNECT ON DATABASE heartbeat_sensitive TO sensitive_app;
    GRANT USAGE ON SCHEMA public TO sensitive_app;

    GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES    IN SCHEMA public TO sensitive_app;
    GRANT USAGE, SELECT                ON ALL SEQUENCES IN SCHEMA public TO sensitive_app;

    -- 트리거 함수 EXECUTE 권한
    -- log_to_audit_sensitive()는 SECURITY DEFINER라 호출 자체엔 권한 불필요하지만
    -- 명시적으로 부여해두는 게 디버깅 시 명료함
    GRANT EXECUTE ON FUNCTION log_to_audit_sensitive() TO sensitive_app;

    ALTER DEFAULT PRIVILEGES FOR ROLE heartbeat IN SCHEMA public
        GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES    TO sensitive_app;
    ALTER DEFAULT PRIVILEGES FOR ROLE heartbeat IN SCHEMA public
        GRANT USAGE, SELECT                  ON SEQUENCES TO sensitive_app;

    SELECT rolname, rolcanlogin, rolsuper, rolcreatedb
    FROM pg_roles WHERE rolname = 'sensitive_app';
EOSQL

echo ""
echo "✅ 옵션 B 적용 완료"
echo ""
echo "다음 단계:"
echo "  1) backend/.env의 DATABASE_URL_* 3개 변경 (아래 diff 참조)"
echo "  2) docker compose restart api"
echo "  3) bash scripts/verify_option_b.sh 로 검증"