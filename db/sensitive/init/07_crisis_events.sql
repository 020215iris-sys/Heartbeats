-- ============================================================
-- 민감 DB — crisis_events 테이블
-- 역할: 위기(자살·자해 위험) 감지 이벤트 기록
-- 설계 의도:
--   - 가장 중요한 테이블 중 하나. 사후 검증에 핵심 증거
--   - conversation_id: 어떤 대화에서 감지됐는지 추적 (같은 DB라 FK 가능)
--   - severity 단계별 대응:
--     'info'    : 모니터링만 (점수 낮지만 주의)
--     'warning' : 1393 안내 노출
--     'crisis'  : 1393 + 보호자 알림 + 상담 강제 종료
--   - guardian_notified: 보호자에게 알림이 실제 발송됐는지
--   - resolved: 운영자가 후속 조치 완료 표시
-- ============================================================

CREATE TABLE crisis_events (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL,           -- 크로스 DB (FK 없음)
    conversation_id     UUID REFERENCES conversations(id) ON DELETE SET NULL,
    crisis_score        REAL NOT NULL,           -- 0.0~1.0
    severity            VARCHAR(20) NOT NULL,
    -- severity 범주: 'info' / 'warning' / 'crisis'
    action_taken        VARCHAR(255),            -- '1393_displayed', 'guardian_notified', 'session_ended' 등 (콤마 구분)
    guardian_notified   BOOLEAN NOT NULL DEFAULT FALSE,
    resolved            BOOLEAN NOT NULL DEFAULT FALSE,
    occurred_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 미해결 위기 이벤트 우선 조회 (운영자 대시보드)
CREATE INDEX idx_crisis_unresolved ON crisis_events(occurred_at DESC)
    WHERE resolved = FALSE;
-- 사용자별 위기 이력
CREATE INDEX idx_crisis_user ON crisis_events(user_id, occurred_at DESC);
-- 고위험 이벤트 빠르게
CREATE INDEX idx_crisis_severity ON crisis_events(severity, occurred_at DESC)
    WHERE severity = 'crisis';
