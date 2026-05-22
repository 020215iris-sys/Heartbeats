-- 03_classifications.sql
-- db_sensitive · CLASSIFICATIONS — 1회 선별(설문) 실행 단위
-- 의존성: 없음 (user_id 는 general.users.id 논리 FK — REFERENCES 불가)
CREATE TABLE classifications (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID        NOT NULL,        -- 논리 FK → general.users.id
    compound_flags      JSONB,                       -- 복합 질환 플래그
    selected_prompt_key VARCHAR(50),                 -- 라우팅된 프롬프트 키
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at          TIMESTAMPTZ                  -- soft delete
);
CREATE INDEX idx_cls_user_id ON classifications(user_id);