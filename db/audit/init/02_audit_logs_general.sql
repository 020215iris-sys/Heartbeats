-- 02_audit_logs_general.sql
-- db_audit · AUDIT_LOGS_GENERAL — 일반 DB 관련 행위 감사 로그
-- append-only(INSERT only) 원칙으로 운영 → 변조 불가(immutability)
CREATE TABLE audit_logs_general (
    id            BIGSERIAL   PRIMARY KEY,           -- 단조 증가 정수 PK
    user_id       UUID,                              -- 논리 FK (비로그인 행위는 NULL)
    action        VARCHAR(50) NOT NULL,              -- 예: LOGIN, UPDATE_PROFILE
    resource_type VARCHAR(50) NOT NULL,              -- 예: users, sessions
    resource_id   UUID,                              -- 대상 레코드 id
    ip_address    INET,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_alg_user_id    ON audit_logs_general(user_id);
CREATE INDEX idx_alg_created_at ON audit_logs_general(created_at);  -- 기간별 조회용