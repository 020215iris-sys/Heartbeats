-- 03_sessions.sql
-- db_general · SESSIONS — JWT refresh token 보관
-- stateless 원칙: access token은 저장하지 않고 refresh token만 저장
CREATE TABLE sessions (
    id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    refresh_token VARCHAR(512) NOT NULL UNIQUE,            -- ERD: UK
    user_agent    VARCHAR(255),
    ip_address    INET,
    expires_at    TIMESTAMPTZ  NOT NULL,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    revoked_at    TIMESTAMPTZ
);
CREATE INDEX idx_sessions_user_id    ON sessions(user_id);
CREATE INDEX idx_sessions_expires_at ON sessions(expires_at);  -- 만료 세션 정리 조회용