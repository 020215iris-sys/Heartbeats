-- ============================================================
-- 민감 DB (heartbeat_sensitive) — 확장 기능
-- 역할: UUID 생성, 암호화, 벡터 검색 (AI 임베딩)
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 벡터 검색용 (대화 임베딩 저장 → RAG, 유사 발화 검색)
-- pgvector 이미지에 포함됨
CREATE EXTENSION IF NOT EXISTS "vector";

-- 쿼리 모니터링
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
