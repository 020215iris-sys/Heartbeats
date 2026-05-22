-- 04_classification_results.sql
-- db_sensitive · CLASSIFICATION_RESULTS — 카테고리별 선별 결과 (1 classification → N행)
-- 의존성: classifications(03), category_catalog(02)
CREATE TABLE classification_results (
    id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    classification_id UUID        NOT NULL REFERENCES classifications(id) ON DELETE CASCADE,
    category_code     VARCHAR(30) NOT NULL REFERENCES category_catalog(category_code),
    instrument        VARCHAR(30) NOT NULL,
    instrument_ver    VARCHAR(20) NOT NULL,
    responses         JSONB       NOT NULL,          -- 문항별 응답
    total_score       SMALLINT    NOT NULL,
    severity          VARCHAR(20) NOT NULL,          -- 예: PHQ-9 5단계 분류값
    score_delta       SMALLINT,                      -- 직전 회차 대비 변화량(첫 회차 NULL)
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_clsres_classification_id ON classification_results(classification_id);
CREATE INDEX idx_clsres_category_code     ON classification_results(category_code);