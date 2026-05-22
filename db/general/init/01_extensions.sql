-- 01_extensions.sql
-- db_general · 확장 설치 (실행 순서 01 — 테이블보다 먼저)
-- 이미지: pgvector/pgvector:pg16
CREATE EXTENSION IF NOT EXISTS "pgcrypto";  -- 암호 함수·UUID (PG16은 gen_random_uuid 내장이나 명시 확보)
CREATE EXTENSION IF NOT EXISTS "vector";    -- pgvector — 현재 ERD 미사용, 향후 AI 임베딩 대비