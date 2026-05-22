-- 01_extensions.sql
-- db_audit · 확장 설치
-- ⚠️ 이미지가 postgres:16-alpine — pgvector 미포함!
--    'CREATE EXTENSION vector' 를 넣으면 컨테이너 기동이 실패합니다.
--    (audit/01_extensions.sql 이 'M'으로 표시된 게 이 때문일 가능성이 큽니다)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";  -- audit DB는 pgcrypto만