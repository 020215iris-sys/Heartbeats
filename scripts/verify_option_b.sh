#!/bin/bash
# scripts/verify_option_b.sh
# 옵션 B 적용 후 동작 검증
# - ROLE 존재 확인
# - 정상 동작 (SELECT/INSERT) 확인
# - 권한 거부 (TRUNCATE/DISABLE TRIGGER) 확인
# - audit_writer 변조 차단 확인

set -e

if [ -f .env ]; then set -a; . ./.env; set +a; fi
: "${DB_GENERAL_APP_PASSWORD:?}"
: "${DB_SENSITIVE_APP_PASSWORD:?}"
: "${DB_AUDIT_WRITER_PASSWORD:?}"

# ──────────────────────────────────────
# 검증 1: ROLE이 모두 존재하고 SUPERUSER 아님
# ──────────────────────────────────────
echo "═══ 1. ROLE 존재 + 권한 수준 확인 ═══"
echo ""
echo "[general DB]"
docker exec heartbeat_db_general psql -U heartbeat -d heartbeat_general -c "
    SELECT rolname, rolcanlogin, rolsuper, rolcreatedb
    FROM pg_roles
    WHERE rolname IN ('heartbeat', 'general_app')
    ORDER BY rolname;"

echo "[sensitive DB]"
docker exec heartbeat_db_sensitive psql -U heartbeat -d heartbeat_sensitive -c "
    SELECT rolname, rolcanlogin, rolsuper, rolcreatedb
    FROM pg_roles
    WHERE rolname IN ('heartbeat', 'sensitive_app')
    ORDER BY rolname;"

echo "[audit DB] (변경 없음 — 기존 audit_writer 그대로)"
docker exec heartbeat_db_audit psql -U heartbeat -d heartbeat_audit -c "
    SELECT rolname, rolcanlogin, rolsuper, rolcreatedb
    FROM pg_roles
    WHERE rolname IN ('heartbeat', 'audit_writer')
    ORDER BY rolname;"

# ──────────────────────────────────────
# 검증 2: app 계정의 정상 SELECT
#   -h localhost로 password 인증 강제 (peer 인증 우회)
#   PGPASSWORD 환경변수로 비번 전달
# ──────────────────────────────────────
echo ""
echo "═══ 2. app 계정 정상 동작 (SELECT 성공해야 함) ═══"

echo "[general_app] SELECT users"
docker exec -e PGPASSWORD="$DB_GENERAL_APP_PASSWORD" -i heartbeat_db_general \
    psql -U general_app -d heartbeat_general -h localhost \
    -c "SELECT count(*) AS user_count FROM users;"

echo "[sensitive_app] SELECT counseling_sessions"
docker exec -e PGPASSWORD="$DB_SENSITIVE_APP_PASSWORD" -i heartbeat_db_sensitive \
    psql -U sensitive_app -d heartbeat_sensitive -h localhost \
    -c "SELECT count(*) AS session_count FROM counseling_sessions;"

# ──────────────────────────────────────
# 검증 3: 위험 명령은 거부돼야 함
#   || true: psql이 에러 종료 코드를 내도 스크립트 계속 진행
#   2>&1 | grep: 에러 메시지를 stdout으로 합쳐서 grep
# ──────────────────────────────────────
echo ""
echo "═══ 3. 위험 명령 거부 확인 (모두 실패해야 정상) ═══"

echo "[sensitive_app] TRUNCATE 시도..."
docker exec -e PGPASSWORD="$DB_SENSITIVE_APP_PASSWORD" -i heartbeat_db_sensitive \
    psql -U sensitive_app -d heartbeat_sensitive -h localhost \
    -c "TRUNCATE counseling_sessions;" 2>&1 | \
    grep -i "permission denied" >/dev/null && \
    echo "  ✅ TRUNCATE 차단됨" || echo "  ❌ TRUNCATE 통과 (문제!)"

echo "[sensitive_app] DISABLE TRIGGER 시도..."
docker exec -e PGPASSWORD="$DB_SENSITIVE_APP_PASSWORD" -i heartbeat_db_sensitive \
    psql -U sensitive_app -d heartbeat_sensitive -h localhost \
    -c "ALTER TABLE counseling_sessions DISABLE TRIGGER ALL;" 2>&1 | \
    grep -i "must be owner" >/dev/null && \
    echo "  ✅ DISABLE TRIGGER 차단됨" || echo "  ❌ DISABLE TRIGGER 통과 (문제!)"

echo "[sensitive_app] DROP TABLE 시도..."
docker exec -e PGPASSWORD="$DB_SENSITIVE_APP_PASSWORD" -i heartbeat_db_sensitive \
    psql -U sensitive_app -d heartbeat_sensitive -h localhost \
    -c "DROP TABLE conversations;" 2>&1 | \
    grep -i "must be owner" >/dev/null && \
    echo "  ✅ DROP TABLE 차단됨" || echo "  ❌ DROP TABLE 통과 (문제!)"

# ──────────────────────────────────────
# 검증 4: audit_writer가 INSERT는 되지만 UPDATE/DELETE는 안 됨
# ──────────────────────────────────────
echo ""
echo "═══ 4. audit_writer 권한 검증 ═══"

echo "[audit_writer] INSERT 시도 (성공해야 함)..."
docker exec -e PGPASSWORD="$DB_AUDIT_WRITER_PASSWORD" -i heartbeat_db_audit \
    psql -U audit_writer -d heartbeat_audit -h localhost \
    -c "INSERT INTO audit_logs_general(user_id, action, resource_type) VALUES (NULL, 'VERIFY_TEST', 'TEST') RETURNING id;"

echo "[audit_writer] UPDATE 시도 (차단돼야 함)..."
docker exec -e PGPASSWORD="$DB_AUDIT_WRITER_PASSWORD" -i heartbeat_db_audit \
    psql -U audit_writer -d heartbeat_audit -h localhost \
    -c "UPDATE audit_logs_general SET action='HACKED' WHERE action='VERIFY_TEST';" 2>&1 | \
    grep -i "permission denied" >/dev/null && \
    echo "  ✅ UPDATE 차단됨" || echo "  ❌ UPDATE 통과 (문제!)"

echo "[audit_writer] DELETE 시도 (차단돼야 함)..."
docker exec -e PGPASSWORD="$DB_AUDIT_WRITER_PASSWORD" -i heartbeat_db_audit \
    psql -U audit_writer -d heartbeat_audit -h localhost \
    -c "DELETE FROM audit_logs_general WHERE action='VERIFY_TEST';" 2>&1 | \
    grep -i "permission denied" >/dev/null && \
    echo "  ✅ DELETE 차단됨" || echo "  ❌ DELETE 통과 (문제!)"

# ──────────────────────────────────────
# 검증 5: 가장 중요 — fdw 트리거 동작
#   sensitive_app으로 INSERT → 트리거 발동 → audit에 자동 기록되는지
# ──────────────────────────────────────
echo ""
echo "═══ 5. fdw 트리거 동작 검증 (가장 중요) ═══"

# 5-1) sensitive에 sensitive_app으로 테스트 INSERT
echo "[sensitive_app] crisis_events INSERT..."
TEST_USER_ID="00000000-0000-0000-0000-000000099999"
INSERT_RESULT=$(docker exec -e PGPASSWORD="$DB_SENSITIVE_APP_PASSWORD" -i heartbeat_db_sensitive \
    psql -U sensitive_app -d heartbeat_sensitive -h localhost -t -A \
    -c "INSERT INTO crisis_events(user_id, session_id, risk_level, detected_at)
        VALUES ('$TEST_USER_ID', NULL, 'low', now())
        RETURNING id;" 2>&1)

if echo "$INSERT_RESULT" | grep -qiE "(error|denied|fail)"; then
    echo "  ❌ INSERT 자체 실패: $INSERT_RESULT"
    echo "  → fdw가 막혔거나 USER MAPPING 문제. 아래 트러블슈팅 참조."
    exit 1
fi
TEST_ID=$(echo "$INSERT_RESULT" | head -1)
echo "  → 생성된 crisis_event id: $TEST_ID"

# 5-2) audit DB에서 해당 기록 확인
echo "[audit DB] audit_logs_sensitive에서 해당 기록 조회..."
sleep 1   # 트리거 → fdw → audit DB 도착까지 약간의 여유
docker exec heartbeat_db_audit psql -U heartbeat -d heartbeat_audit -c "
    SELECT id, user_id, action, resource_type, resource_id, created_at
    FROM audit_logs_sensitive
    WHERE resource_id = '$TEST_ID'::uuid;"

echo ""
echo "  → 위 결과에 1줄이 보이면 ✅ fdw 트리거 정상"
echo "  → 0줄이면 ❌ USER MAPPING 또는 SECURITY DEFINER 문제 (Phase 1 디버깅 필요)"

echo ""
echo "═══ 검증 완료 ═══"