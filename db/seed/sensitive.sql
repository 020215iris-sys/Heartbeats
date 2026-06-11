-- db/seed/sensitive.sql
-- 개발용 더미 데이터 (sensitive DB)
-- ⚠️ 프로덕션에서는 절대 실행 금지

BEGIN;

-- ============================================
-- 분류 카테고리 마스터
-- 카테고리당 1행. severity_rule은 점수구간→심각도 매핑(jsonb)
-- ============================================
INSERT INTO category_catalog
  (category_code, display_name, instrument, instrument_ver, item_count, max_score, severity_rule, is_active)
VALUES
  ('depression', '우울', 'PHQ-9', '1.0', 9, 27,
   '{"minimal": [0, 4], "mild": [5, 9], "moderate": [10, 14], "moderately_severe": [15, 19], "severe": [20, 27]}'::jsonb,
   TRUE),
  ('anxiety',    '불안', 'GAD-7', '1.0', 7, 21,
   '{"minimal": [0, 4], "mild": [5, 9], "moderate": [10, 14], "severe": [15, 21]}'::jsonb,
   TRUE);

-- ============================================
-- 분류 세션 1개 (test 사용자)
-- ============================================
INSERT INTO classifications (id, user_id, compound_flags, selected_prompt_key, created_at)
VALUES
  ('aaaa1111-1111-1111-1111-111111111111',
   '11111111-1111-1111-1111-111111111111',
   '{"depression_and_anxiety": false}'::jsonb,
   'standard_supportive',
   now());

-- 분류 결과: 우울 12점(중등도)
INSERT INTO classification_results
  (id, classification_id, category_code, instrument, instrument_ver, responses, total_score, severity, score_delta, created_at)
VALUES
  ('bbbb1111-1111-1111-1111-111111111111',
   'aaaa1111-1111-1111-1111-111111111111',
   'depression', 'PHQ-9', '1.0',
   '{"q1": 2, "q2": 1, "q3": 2, "q4": 1, "q5": 2, "q6": 1, "q7": 1, "q8": 1, "q9": 1}'::jsonb,
   12, 'moderate', NULL, now());

-- ============================================
-- 상담 세션 + 대화 + 요약 (한 세트)
-- ============================================
INSERT INTO counseling_sessions
  (id, user_id, classification_id, persona_type, started_at, ended_at, is_active)
VALUES
  ('cccc1111-1111-1111-1111-111111111111',
   '11111111-1111-1111-1111-111111111111',
   'aaaa1111-1111-1111-1111-111111111111',
   '{"code": "empathy", "name": "다온", "version": "v1", "params": {}}'::jsonb,
   now() - interval '1 hour',
   now() - interval '30 minutes',
   FALSE);  -- 종료된 세션이므로 is_active=FALSE

-- 대화 2턴
-- 본문은 AES-256 암호문 자리 → 시드에선 더미 토큰 사용
-- (백엔드 연동 후엔 실제 암호문이 들어감)
INSERT INTO conversations
  (id, session_id, user_id, role, message_type, encrypted_content, encryption_key_id, crisis_score, created_at)
VALUES
  ('dddd1111-1111-1111-1111-111111111111',
   'cccc1111-1111-1111-1111-111111111111',
   '11111111-1111-1111-1111-111111111111',
   'assistant', 'text',
   'ENC::dev-seed::msg1',
   'dev-key-v1',
   0.05,
   now() - interval '55 minutes'),
  ('dddd2222-2222-2222-2222-222222222222',
   'cccc1111-1111-1111-1111-111111111111',
   '11111111-1111-1111-1111-111111111111',
   'user', 'text',
   'ENC::dev-seed::msg2',
   'dev-key-v1',
   0.10,
   now() - interval '54 minutes');

-- 요약
INSERT INTO summaries
  (id, session_id, user_id, main_complaint, risk_level, suicidal_mentioned,
   core_topics, next_session_notes, prompt_adjustment, created_at)
VALUES
  ('eeee1111-1111-1111-1111-111111111111',
   'cccc1111-1111-1111-1111-111111111111',
   '11111111-1111-1111-1111-111111111111',
   '우울과 무기력감과 관련된 정서적 어려움',
   '중간',
   false,
   '["우울","무기력감","실직불안","정서조절","자존감"]'::jsonb,
   '실직과 관련된 불안과 우울 경험 탐색 필요',
   '["emotional_support","self_care","career_support"]'::jsonb,
   now() - interval '30 minutes');

COMMIT;

SELECT 'category_catalog: '        || count(*)::text FROM category_catalog;
SELECT 'classifications: '         || count(*)::text FROM classifications;
SELECT 'classification_results: '  || count(*)::text FROM classification_results;
SELECT 'counseling_sessions: '     || count(*)::text FROM counseling_sessions;
SELECT 'conversations: '           || count(*)::text FROM conversations;
SELECT 'summaries: '                || count(*)::text FROM summaries;
