-- ============================================================
-- 감사 DB — audit_logs_general 테이블
-- 역할: 일반 DB 자원에 대한 접근/변경 감사 로그
-- 설계 의도:
--   - 일반 DB의 user/session/guardian 관련 작업 추적
--   - 별도 DB로 분리하여 INSERT only 권한 부여 가능 → 변조 방지
--   - 운영 DB가 침해돼도 감사 기록은 보존
--   - resource_type/resource_id로 어떤 객체에 대한 작업인지 식별
-- ============================================================

CREATE TABLE audit_logs_general (
    id              BIGSERIAL PRIMARY KEY,
    user_id         UUID,                            -- 크로스 DB (FK 없음). 익명 접근도 있어 NULL 허용
    action          VARCHAR(50) NOT NULL,            -- 'login', 'update_profile', 'register_guardian' 등
    resource_type   VARCHAR(50),                     -- 'user', 'session', 'guardian_consent'
    resource_id     UUID,                            -- 작업 대상 객체의 id
    ip_address      INET,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 시간 범위 조회 ("최근 1시간 로그") 가장 잦음
CREATE INDEX idx_audit_general_time ON audit_logs_general(created_at DESC);
-- 특정 사용자 이력 조회
CREATE INDEX idx_audit_general_user ON audit_logs_general(user_id, created_at DESC);
