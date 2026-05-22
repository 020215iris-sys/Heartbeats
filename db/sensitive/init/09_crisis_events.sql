-- 09_crisis_events.sql
-- db_sensitive · CRISIS_EVENTS — 위기 감지 이벤트 (안전 기록 — 보존 우선)
-- conversation_id 에 CASCADE 미적용: 대화가 삭제돼도 위기 기록은 남아야 하므로
-- (기본 NO ACTION = 위기 이벤트가 참조 중인 대화는 물리 삭제 자체가 차단됨)
-- 의존성: conversations(06)
CREATE TABLE crisis_events (
    id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID        NOT NULL,          -- 논리 FK
    conversation_id   UUID        NOT NULL REFERENCES conversations(id),
    crisis_score      REAL        NOT NULL,          -- 위기 점수 0.0~1.0
    severity          VARCHAR(20) NOT NULL,          -- 위험도 등급
    action_taken      VARCHAR(100),                  -- 취해진 조치
    guardian_notified BOOLEAN     NOT NULL DEFAULT FALSE,
    resolved          BOOLEAN     NOT NULL DEFAULT FALSE,
    occurred_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_crisis_user_id         ON crisis_events(user_id);
CREATE INDEX idx_crisis_conversation_id ON crisis_events(conversation_id);