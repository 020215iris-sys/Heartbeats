-- db/seed/general.sql
-- 개발용 더미 데이터 (general DB)
-- ⚠️ 프로덕션에서는 절대 실행 금지
-- 사용: docker exec -i heartbeat_db_general psql -U heartbeat -d heartbeat_general < db/seed/general.sql

BEGIN;

-- ============================================
-- 사용자 3명: 일반·관리자·미성년(보호자 동의 대상)
-- ============================================
-- 평문 비번은 모두 'Test1234!' (bcrypt 해시)
INSERT INTO users (id, email, password_hash, phone, name, role, created_at) VALUES
  ('11111111-1111-1111-1111-111111111111',
   'test@example.com',
   '$2b$12$LQ3HnFKxYxKxKxKxKxKxKuJ3o6hKxKxKxKxKxKxKxKxKxKxKxKxK',
   '010-1111-1111', '테스트유저', 'user', now()),

  ('22222222-2222-2222-2222-222222222222',
   'admin@example.com',
   '$2b$12$LQ3HnFKxYxKxKxKxKxKxKuJ3o6hKxKxKxKxKxKxKxKxKxKxKxKxK',
   '010-2222-2222', '관리자', 'admin', now()),

  ('33333333-3333-3333-3333-333333333333',
   'minor@example.com',
   '$2b$12$LQ3HnFKxYxKxKxKxKxKxKuJ3o6hKxKxKxKxKxKxKxKxKxKxKxKxK',
   '010-3333-3333', '미성년사용자', 'user', now());

-- ============================================
-- 보호자 동의: 미성년 사용자에 대해
-- ============================================
INSERT INTO guardian_consents (id, user_id, guardian_phone, consent_at) VALUES
  ('44444444-4444-4444-4444-444444444444',
   '33333333-3333-3333-3333-333333333333',
   '010-9999-9999',
   now());

-- sessions는 로그인 API가 자동 생성 → seed에서 만들지 않음

COMMIT;

-- 확인
SELECT 'users 시드 완료, 개수: ' || count(*)::text FROM users;
SELECT 'guardian_consents 시드 완료, 개수: ' || count(*)::text FROM guardian_consents;