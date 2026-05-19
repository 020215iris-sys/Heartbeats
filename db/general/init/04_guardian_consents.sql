-- ============================================================
-- 일반 DB — guardian_consents 테이블
-- 역할: 보호자 알림 동의 이력 (위기 상황 시 알림 보낼 보호자 등록)
-- 설계 의도:
--   - 사용자가 등록한 보호자 전화번호
--   - 동의/철회를 모두 기록 (단순 boolean이 아니라 이력으로 관리)
--   - revoked_at: 철회 시점 (재동의해도 이력은 남김)
-- ============================================================

CREATE TABLE guardian_consents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    guardian_phone  VARCHAR(20) NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    consented_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_at      TIMESTAMPTZ
);

-- 위기 발생 시 활성 보호자 빠르게 찾기 위한 부분 인덱스
CREATE INDEX idx_guardian_active ON guardian_consents(user_id) WHERE is_active = TRUE;
