-- ============================================================
-- 민감 DB — summaries 테이블
-- 역할: 상담 종료 후 자동 생성되는 요약 (다음 상담 연속성 보장)
-- 설계 의도:
--   - 한 세션당 요약 1개 (1:1 관계, UNIQUE 제약으로 강제)
--   - main_complaint: 주요 호소 내용 (자유 기술)
--   - risk_level: 위험도 분류
--   - next_session_notes: 다음 상담에서 이어갈 내용
--   - prompt_adjustment: 다음 상담 시 프롬프트 조정 가이드
-- ============================================================

CREATE TABLE summaries (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id          UUID NOT NULL UNIQUE REFERENCES counseling_sessions(id) ON DELETE CASCADE,
    -- UNIQUE: 한 세션에 요약 1개만
    user_id             UUID NOT NULL,           -- 크로스 DB (FK 없음)
    main_complaint      TEXT,                    -- 주요 호소 내용
    risk_level          VARCHAR(20) NOT NULL,
    -- risk_level 범주: 'low' / 'medium' / 'high'
    suicidal_mentioned  BOOLEAN NOT NULL DEFAULT FALSE,
    core_topics         TEXT,                    -- 이번 상담의 핵심 주제
    next_session_notes  TEXT,                    -- 다음 상담 이어갈 내용
    prompt_adjustment   VARCHAR(255),            -- 권장 상담 방향 조정
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 사용자별 요약 시간순 조회
CREATE INDEX idx_summaries_user ON summaries(user_id, created_at DESC);
-- 고위험 요약 빠르게 찾기 (운영자 모니터링용)
CREATE INDEX idx_summaries_high_risk ON summaries(created_at DESC)
    WHERE risk_level = 'high' OR suicidal_mentioned = TRUE;
