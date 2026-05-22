-- 01_extensions.sql
-- db_sensitive · 확장 설치 / 이미지: pgvector/pgvector:pg16
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";    -- 향후 AI 임베딩 대비 (현재 ERD 미사용)