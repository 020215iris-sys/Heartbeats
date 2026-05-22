-- 04_guardian_consents.sql
-- db_general · GUARDIAN_CONSENTS — 보호자 알림 동의 이력
CREATE TABLE guardian_consents (
    id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id        UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    guardian_phone VARCHAR(20) NOT NULL,
    is_active      BOOLEAN     NOT NULL DEFAULT TRUE,
    consented_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_at     TIMESTAMPTZ                            -- 동의 철회 시각 (NULL=유효)
);
CREATE INDEX idx_guardian_consents_user_id ON guardian_consents(user_id);