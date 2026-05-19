-- ============================================================
-- 일반 DB — users 테이블
-- 역할: 회원 기본 정보 (이메일, 비밀번호 해시, 권한)
-- 설계 의도:
--   - id를 UUID로: 순차 정수는 사용자 수 노출시키는 보안 약점
--   - role: 사용자 유형 구분 (일반/보호자/관리자)
--   - hashed_password: 평문 비밀번호 절대 저장 X (bcrypt 등 해시값)
--   - deleted_at: 소프트 삭제 (실제 행은 안 지움, 감사 추적용)
-- ============================================================

CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) NOT NULL UNIQUE,
    nickname        VARCHAR(50),
    hashed_password VARCHAR(255) NOT NULL,
    phone_number    VARCHAR(20),
    role            VARCHAR(20) NOT NULL DEFAULT 'user',
    -- role 범주: 'user' (일반 사용자) / 'guardian' (보호자) / 'admin' (관리자)
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login_at   TIMESTAMPTZ,
    deleted_at      TIMESTAMPTZ
);

-- 로그인 시 email로 찾는 쿼리가 가장 잦음. 활성 회원만 인덱싱 (크기 최소화)
CREATE INDEX idx_users_email ON users(email) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_phone ON users(phone_number) WHERE deleted_at IS NULL;
