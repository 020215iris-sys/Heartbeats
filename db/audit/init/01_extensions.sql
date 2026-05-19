-- ============================================================
-- 감사 DB (heartbeat_audit) — 확장 기능
-- 역할: UUID 생성만. 단순한 DB.
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 감사 DB는 가벼운 INSERT 위주라 모니터링도 가벼움
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
