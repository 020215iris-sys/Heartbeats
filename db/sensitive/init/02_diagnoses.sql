-- ============================================================
-- 민감 DB — diagnoses 테이블
-- 역할: 자가검진 결과 (PHQ-9, GAD-7 점수와 분류)
-- 설계 의도:
--   - 개별 문항 응답은 저장 안 하고 집계 점수만 저장 (팀 결정)
--   - user_id는 일반 DB의 users.id 참조이지만 크로스 DB라 FK 못 검
--     → 정합성은 FastAPI에서 보장
--   - compound_flags: 복합 질환 표시 (예: {"high_phq9": true, "high_gad7": true})
--   - selected_prompt_key: 진단 결과에 따라 어떤 상담 프롬프트 라우팅했는지 기록
--
-- 점수 범위:
--   PHQ-9: 0~27 (9문항 × 0~3점)
--   GAD-7: 0~21 (7문항 × 0~3점)
--
-- phq9_severity 5단계:
--   'minimal'           (0~4)   정상
--   'mild'              (5~9)   경도
--   'moderate'          (10~14) 중등도
--   'moderately_severe' (15~19) 중등도~중증
--   'severe'            (20~27) 중증
--
-- gad7_severity 4단계:
--   'minimal'  (0~4)   정상
--   'mild'     (5~9)   경도
--   'moderate' (10~14) 중등도
--   'severe'   (15~21) 중증
-- ============================================================

CREATE TABLE diagnoses (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL,           -- 크로스 DB 참조 (FK 없음)
    phq9_score          SMALLINT,                -- 0~27
    gad7_score          SMALLINT,                -- 0~21
    phq9_severity       VARCHAR(30),
    gad7_severity       VARCHAR(30),
    phq9_delta          SMALLINT,                -- 이전 회차 대비 변화
    gad7_delta          SMALLINT,
    compound_flags      JSONB,                   -- 복합 질환 플래그
    selected_prompt_key VARCHAR(50),             -- 라우팅된 프롬프트 식별자
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at          TIMESTAMPTZ
);

-- 사용자의 진단 이력 시간순 조회
CREATE INDEX idx_diagnoses_user ON diagnoses(user_id, created_at DESC) 
    WHERE deleted_at IS NULL;
