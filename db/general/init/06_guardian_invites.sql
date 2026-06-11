-- 06_guardian_invites.sql
-- db_general · GUARDIAN_INVITES — 보호자 가입 게이트키퍼 + 영구 연결 매핑
-- 의존성: users(02)
-- 흐름:
--   1) ward(피보호자)가 POST /guardian/invite로 8자리 숫자 코드 발급 (pending, 1시간 만료)
--   2) ward가 보호자에게 코드 전달 (현재: 복사 / 향후: SMS 자동)
--   3) 보호자가 /auth/signup에서 invite_code 입력 → 가입 + 연결 (후속 PR)
-- RBAC: 05_app_role.sh의 ALTER DEFAULT PRIVILEGES로 general_app에 CRUD 자동 부여됨

CREATE TABLE guardian_invites (
    id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    code             VARCHAR(8)   NOT NULL UNIQUE,
    ward_user_id     UUID         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    guardian_user_id UUID                  REFERENCES users(id) ON DELETE SET NULL,
    status           VARCHAR(20)  NOT NULL DEFAULT 'pending',
    attempt_count    INTEGER      NOT NULL DEFAULT 0,
    expires_at       TIMESTAMPTZ  NOT NULL,
    accepted_at      TIMESTAMPTZ,
    revoked_at       TIMESTAMPTZ,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT guardian_invites_status_check
        CHECK (status IN ('pending', 'accepted', 'expired', 'revoked')),
    CONSTRAINT guardian_invites_attempt_count_nonneg
        CHECK (attempt_count >= 0),
    CONSTRAINT guardian_invites_code_format
        CHECK (code ~ '^[0-9]{8}$')
);

CREATE INDEX idx_gi_ward_user_id     ON guardian_invites(ward_user_id);
CREATE INDEX idx_gi_guardian_user_id ON guardian_invites(guardian_user_id);

-- 부분 인덱스: pending인 행만 → 만료 정리 배치 효율화 + 인덱스 사이즈 ↓
CREATE INDEX idx_gi_expires_at_pending
    ON guardian_invites(expires_at)
    WHERE status = 'pending';