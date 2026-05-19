-- ============================================================
-- 민감 DB — counseling_sessions 테이블
-- 역할: AI 상담 세션 메타 정보 (시작/종료 시각, 페르소나 등)
-- 설계 의도:
--   - 한 세션 = 한 번의 상담 대화 흐름
--   - diagnosis_id: 어떤 진단 결과를 기반으로 시작된 상담인지 (같은 DB라 FK 가능)
--   - persona_type: 어떤 상담사 스타일로 진행했는지
--   - is_active: 현재 진행 중인 세션인지 (한 사용자 동시 1개만 권장)
-- ============================================================

CREATE TABLE counseling_sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL,           -- 크로스 DB (FK 없음)
    diagnosis_id    UUID REFERENCES diagnoses(id) ON DELETE SET NULL,
    persona_type    VARCHAR(20) NOT NULL,
    -- persona_type 범주: 'empathy' (공감형) / 'coaching' (코칭형) / 'neutral' (중립형)
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at        TIMESTAMPTZ,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    deleted_at      TIMESTAMPTZ
);

-- 사용자별 상담 이력 조회
CREATE INDEX idx_counseling_user ON counseling_sessions(user_id, started_at DESC)
    WHERE deleted_at IS NULL;
-- 진행 중인 세션 빠르게 찾기
CREATE INDEX idx_counseling_active ON counseling_sessions(user_id) 
    WHERE is_active = TRUE AND deleted_at IS NULL;
