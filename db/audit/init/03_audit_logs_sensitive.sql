-- 03_audit_logs_sensitive.sql
-- db_audit · AUDIT_LOGS_SENSITIVE — 민감 DB 관련 행위 감사 로그
-- 구조는 audit_logs_general 과 동일, 대상 DB만 다름 (분리 보관 원칙)
CREATE TABLE audit_logs_sensitive (
    id            BIGSERIAL   PRIMARY KEY,
    user_id       UUID,                              -- 논리 FK
    action        VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,              -- 예: conversations, crisis_events
    resource_id   UUID,
    ip_address    INET,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_als_user_id    ON audit_logs_sensitive(user_id);
CREATE INDEX idx_als_created_at ON audit_logs_sensitive(created_at);