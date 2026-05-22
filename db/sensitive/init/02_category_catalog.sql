-- 02_category_catalog.sql
-- db_sensitive · CATEGORY_CATALOG — 분류 항목 정의
-- 카테고리를 '컬럼'이 아닌 '행'으로 관리 → 항목 추가 시 스키마 변경 불필요
-- 의존성: 없음
CREATE TABLE category_catalog (
    category_code  VARCHAR(30) PRIMARY KEY,        -- 예: 'depression' (ERD: PK)
    display_name   VARCHAR(50) NOT NULL,           -- 예: '우울'
    instrument     VARCHAR(30) NOT NULL,           -- 측정도구, 예: 'PHQ-9'
    instrument_ver VARCHAR(20) NOT NULL,           -- 도구 버전
    item_count     SMALLINT    NOT NULL,           -- 문항 수
    max_score      SMALLINT    NOT NULL,           -- 만점
    severity_rule  JSONB       NOT NULL,           -- 점수구간→심각도 규칙(데이터로 보관)
    is_active      BOOLEAN     NOT NULL DEFAULT TRUE
);