-- ============================================================
-- 일반 DB — sessions 테이블
-- 역할: JWT refresh token 관리 (한 사용자가 여러 기기 로그인 가능)
-- 설계 의도:
--   - access_token이 아니라 refresh_token만 저장
--     (access_token은 짧은 수명, 메모리만 사용. refresh는 길어서 DB 필요)
--   - 같은 사용자가 폰/PC 등 여러 기기에서 동시 로그인 → 여러 행
--   - 강제 로그아웃 = 해당 행 삭제
-- ============================================================

CREATE TABLE sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    refresh_token   VARCHAR(512) NOT NULL UNIQUE,
    user_agent      TEXT,                -- 어떤 브라우저/앱에서 로그인했는지
    ip_address      INET,                -- 로그인한 IP (보안 모니터링용)
    expires_at      TIMESTAMPTZ NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 사용자의 활성 세션 조회
CREATE INDEX idx_sessions_user ON sessions(user_id);
-- 만료된 세션 정기 청소용 (Celery beat 등에서 사용)
CREATE INDEX idx_sessions_expires ON sessions(expires_at);
