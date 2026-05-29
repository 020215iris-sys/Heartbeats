-- db/seed/general.sql
-- 개발용 더미 데이터 (general DB)
-- ⚠️ 프로덕션에서는 절대 실행 금지
-- 사용: docker exec -i heartbeat_db_general psql -U heartbeat -d heartbeat_general < db/seed/general.sql

BEGIN;

-- 사용자 3명: 일반·관리자·미성년(보호자 동의 대상)
-- 평문 비번은 모두 'Test1234!' (bcrypt 해시)
INSERT INTO users (id, email, nickname, hashed_password, phone_number, gender, birth_date, role, is_active, created_at)
VALUES
  ('11111111-1111-1111-1111-111111111111',
   'test@example.com', '테스트유저',
   '$2b$12$AtLOiRVireV9EIXls.49cO2u4uLfJ3aun6zF.D3rnajqKVq1JQqBG',
   '010-1111-1111', 'female', '1995-04-12', 'user',  TRUE, now()),

  ('22222222-2222-2222-2222-222222222222',
   'admin@example.com', '관리자',
   '$2b$12$AtLOiRVireV9EIXls.49cO2u4uLfJ3aun6zF.D3rnajqKVq1JQqBG',
   '010-2222-2222', 'undisclosed', '1985-09-30', 'admin', TRUE, now()),

  ('33333333-3333-3333-3333-333333333333',
   'minor@example.com', '미성년사용자',
   '$2b$12$AtLOiRVireV9EIXls.49cO2u4uLfJ3aun6zF.D3rnajqKVq1JQqBG',
   '010-3333-3333', 'male', '2012-07-22', 'user',  TRUE, now());

-- 보호자 동의: 미성년 사용자에 대해
INSERT INTO guardian_consents (id, user_id, guardian_phone, is_active, consented_at)
VALUES
  ('44444444-4444-4444-4444-444444444444',
   '33333333-3333-3333-3333-333333333333',
   '010-9999-9999',
   TRUE,
   now());

COMMIT;

SELECT 'users 시드 완료, 개수: ' || count(*)::text FROM users;
SELECT 'guardian_consents 시드 완료, 개수: ' || count(*)::text FROM guardian_consents;