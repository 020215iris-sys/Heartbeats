-- 05_counseling_sessions.sql
-- db_sensitive · COUNSELING_SESSIONS — 상담 1회차 단위
-- 의존성: classifications(03)
CREATE TABLE counseling_sessions (
    id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID        NOT NULL,          -- 논리 FK → general.users.id
    classification_id UUID        NOT NULL REFERENCES classifications(id),
    persona_type      VARCHAR(30),                   -- 상담사 페르소나
    started_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at          TIMESTAMPTZ,                   -- 진행 중이면 NULL
    is_active         BOOLEAN     NOT NULL DEFAULT TRUE,
    deleted_at        TIMESTAMPTZ                    -- soft delete
);
CREATE INDEX idx_cs_user_id           ON counseling_sessions(user_id);
CREATE INDEX idx_cs_classification_id ON counseling_sessions(classification_id);