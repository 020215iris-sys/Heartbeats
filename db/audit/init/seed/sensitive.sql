-- db/seed/sensitive.sql
-- 개발용 더미 데이터 (sensitive DB)
-- ⚠️ 프로덕션에서는 절대 실행 금지

BEGIN;

-- ============================================
-- 분류 카테고리 마스터 (PHQ-9, GAD-7)
-- 이건 시드라기보다 마스터 데이터에 가까움
-- 실제 운영에서도 필요한 기본 카테고리
-- ============================================
INSERT INTO category_catalog (category_code, name, instrument, severity_rule) VALUES
  ('PHQ9_MINIMAL',  '최소 우울',     'PHQ-9', '0-4점'),
  ('PHQ9_MILD',     '경도 우울',     'PHQ-9', '5-9점'),
  ('PHQ9_MODERATE', '중등도 우울',   'PHQ-9', '10-14점'),
  ('PHQ9_MODSEVERE','중등고도 우울', 'PHQ-9', '15-19점'),
  ('PHQ9_SEVERE',   '고도 우울',     'PHQ-9', '20-27점'),
  ('GAD7_MINIMAL',  '최소 불안',     'GAD-7', '0-4점'),
  ('GAD7_MILD',     '경도 불안',     'GAD-7', '5-9점'),
  ('GAD7_MODERATE', '중등도 불안',   'GAD-7', '10-14점'),
  ('GAD7_SEVERE',   '고도 불안',     'GAD-7', '15-21점');

-- ============================================
-- 분류 세션 (test@example.com 사용자의 1회)
-- ============================================
INSERT INTO classifications (id, user_id, created_at) VALUES
  ('aaaa1111-1111-1111-1111-111111111111',
   '11111111-1111-1111-1111-111111111111',  -- 논리 참조: general.users
   now());

-- 분류 결과: PHQ-9 12점 (중등도)
INSERT INTO classification_results
  (id, classification_id, category_code, instrument, instrument_ver, score, severity, responses, created_at) VALUES
  ('bbbb1111-1111-1111-1111-111111111111',
   'aaaa1111-1111-1111-1111-111111111111',
   'PHQ9_MODERATE',
   'PHQ-9', '1.0',
   12,
   '중등도',
   '{"q1": 2, "q2": 1, "q3": 2, "q4": 1, "q5": 2, "q6": 1, "q7": 1, "q8": 1, "q9": 1}'::jsonb,
   now());

-- ============================================
-- 상담 세션 + 대화 + 요약 (한 세트)
-- ============================================
INSERT INTO counseling_sessions (id, user_id, classification_id, started_at, ended_at) VALUES
  ('cccc1111-1111-1111-1111-111111111111',
   '11111111-1111-1111-1111-111111111111',
   'aaaa1111-1111-1111-1111-111111111111',
   now() - interval '1 hour',
   now() - interval '30 minutes');

INSERT INTO conversations (id, counseling_session_id, user_id, message_type, content, created_at) VALUES
  ('dddd1111-1111-1111-1111-111111111111',
   'cccc1111-1111-1111-1111-111111111111',
   '11111111-1111-1111-1111-111111111111',
   'ai',  '오늘은 좀 더 편하게 말씀하셔도 돼요. 오늘 기분은 어떠세요?',
   now() - interval '55 minutes'),
  ('dddd2222-2222-2222-2222-222222222222',
   'cccc1111-1111-1111-1111-111111111111',
   '11111111-1111-1111-1111-111111111111',
   'user', '오늘은 좀 괜찮아요. 어제는 좀 힘들었는데 오늘은 좀 나아요.',
   now() - interval '54 minutes');

INSERT INTO summaries
  (id, session_id, user_id, main_complaint, risk_level, suicidal_mentioned,
   core_topics, next_session_notes, prompt_adjustment, created_at) VALUES
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

-- voice_files / crisis_events는 운영 중 자동 생성되는 데이터라 시드 없음

COMMIT;

-- 확인
SELECT 'category_catalog: ' || count(*)::text FROM category_catalog;
SELECT 'classifications: ' || count(*)::text FROM classifications;
SELECT 'classification_results: ' || count(*)::text FROM classification_results;
SELECT 'counseling_sessions: ' || count(*)::text FROM counseling_sessions;
SELECT 'conversations: ' || count(*)::text FROM conversations;
SELECT 'summaries: ' || count(*)::text FROM summaries;