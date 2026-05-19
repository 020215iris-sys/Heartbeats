-- ============================================================
-- 감사 DB — audit_logs_sensitive 테이블
-- 역할: 민감 DB 자원 접근/변경에 대한 감사 로그
-- 설계 의도:
--   - 정신건강 데이터(진단, 상담, 위기) 접근은 모두 여기에 기록
--   - 일반 로그와 같은 DB에 두지만 테이블 분리 (권한·조회 분리 용이)
--   - INSERT only 원칙
--   - 분쟁/사고 시 법적 증거로 사용 가능해야 함
-- ============================================================

CREATE TABLE audit_logs_sensitive (
    id              BIGSERIAL PRIMARY KEY,
    user_id         UUID,                            -- 크로스 DB (FK 없음). 접근한 사용자
    action          VARCHAR(50) NOT NULL,            -- 'view_diagnosis', 'view_conversation' 등
    resource_type   VARCHAR(50),                     -- 'diagnosis', 'conversation', 'summary'
    resource_id     UUID,
    ip_address      INET,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 시간 범위 조회
CREATE INDEX idx_audit_sensitive_time ON audit_logs_sensitive(created_at DESC);
-- 특정 사용자 데이터 접근 이력 (개인정보 열람 청구 대응)
CREATE INDEX idx_audit_sensitive_user ON audit_logs_sensitive(user_id, created_at DESC);
-- 특정 자원에 누가 접근했는지 (사고 발생 시 추적)
CREATE INDEX idx_audit_sensitive_resource ON audit_logs_sensitive(resource_type, resource_id);
