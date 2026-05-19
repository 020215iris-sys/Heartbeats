-- ============================================================
-- 민감 DB — conversations 테이블
-- 역할: 상담 대화 한 줄 한 줄을 저장 (user 발화, assistant 응답)
-- 설계 의도:
--   - role: 누가 한 말인지 ('user' 또는 'assistant')
--   - message_type: 메시지 종류 분류
--   - encrypted_content: AES-256 암호화된 본문 (FastAPI에서 암호화 후 저장)
--   - encryption_key_id: 어떤 키로 암호화했는지 (키 로테이션 대비)
--   - crisis_score: 위기 키워드 감지 점수 (0.0~1.0, 임계값 넘으면 위기 이벤트 발생)
-- ============================================================

CREATE TABLE conversations (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id          UUID NOT NULL REFERENCES counseling_sessions(id) ON DELETE CASCADE,
    user_id             UUID NOT NULL,           -- 크로스 DB (FK 없음)
    role                VARCHAR(20) NOT NULL,
    -- role 범주: 'user' (사용자 발화) / 'assistant' (AI 응답)
    message_type        VARCHAR(20) NOT NULL DEFAULT 'text',
    -- message_type 범주: 'text' / 'system' / 'crisis' / 'summary'
    encrypted_content   TEXT NOT NULL,           -- AES-256 암호화된 본문
    encryption_key_id   VARCHAR(50) NOT NULL,    -- 키 식별자
    crisis_score        REAL,                    -- 0.0~1.0
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at          TIMESTAMPTZ
);

-- 한 세션의 대화 시간순 조회 (가장 잦은 쿼리)
CREATE INDEX idx_conversations_session ON conversations(session_id, created_at)
    WHERE deleted_at IS NULL;
-- 위기 점수 높은 메시지 빠르게 찾기 (부분 인덱스)
CREATE INDEX idx_conversations_crisis ON conversations(user_id, created_at DESC)
    WHERE crisis_score >= 0.7;
