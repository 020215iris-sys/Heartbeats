-- ============================================================
-- 일반 DB (heartbeat_general) — 확장 기능
-- 역할: UUID 자동 생성, 쿼리 모니터링
-- ============================================================

-- gen_random_uuid() 함수 (UUID 자동 생성)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 쿼리 성능 모니터링 (선택)
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
