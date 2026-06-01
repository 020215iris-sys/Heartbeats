-- 06_conversations.sql
-- db_sensitive · CONVERSATIONS — 상담 대화 메시지
-- 본문(encrypted_content)은 AES-256 암호문으로만 저장 (평문 금지)
-- 의존성: counseling_sessions(05)
CREATE TABLE conversations (
    id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id        UUID        NOT NULL REFERENCES counseling_sessions(id) ON DELETE CASCADE,
    user_id           UUID        NOT NULL,                  -- 논리 FK
    role              VARCHAR(20) NOT NULL,                  -- user / assistant
    message_type      VARCHAR(20) NOT NULL DEFAULT 'text',   -- text / voice
    encrypted_content BYTEA       NOT NULL,                  -- 본문(encrypted_content)은 AES-256-GCM 암호문 바이트로 저장 (W1: 투명 UTF-8 헬퍼)
    encryption_key_id VARCHAR(50) NOT NULL,                  -- 사용한 암호화 키 식별자
    crisis_score      REAL,                                  -- 위기 점수 0.0~1.0
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at        TIMESTAMPTZ                            -- soft delete
);
CREATE INDEX idx_conv_session_id ON conversations(session_id);
CREATE INDEX idx_conv_user_id    ON conversations(user_id);