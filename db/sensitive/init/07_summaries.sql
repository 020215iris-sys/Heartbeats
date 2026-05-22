-- 07_summaries.sql
-- db_sensitive · SUMMARIES — 상담 종료 후 자동 요약 (다음 상담 연속성)
-- 의존성: counseling_sessions(05)
CREATE TABLE summaries (
    id                 UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id         UUID        NOT NULL REFERENCES counseling_sessions(id) ON DELETE CASCADE,
    user_id            UUID        NOT NULL,         -- 논리 FK
    main_complaint     TEXT,                         -- 주요 호소 내용
    risk_level         VARCHAR(20),                  -- 낮음/중간/높음
    suicidal_mentioned BOOLEAN     NOT NULL DEFAULT FALSE,
    core_topics        TEXT,                         -- 핵심 주제
    next_session_notes TEXT,                         -- 다음 상담 이어갈 내용
    prompt_adjustment  VARCHAR(255),                 -- 권장 상담 방향 조정
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_sum_session_id ON summaries(session_id);
CREATE INDEX idx_sum_user_id    ON summaries(user_id);