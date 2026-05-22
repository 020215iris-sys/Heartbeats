-- 02_users.sql
-- db_general · USERS — 모든 user_id 의 원본 (민감·감사 DB가 논리적으로 참조)
CREATE TABLE users (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) NOT NULL UNIQUE,          -- ERD: UK
    nickname        VARCHAR(50)  NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,                 -- 해시값만 저장(평문 금지)
    phone_number    VARCHAR(20),
    role            VARCHAR(20)  NOT NULL DEFAULT 'user',  -- user/guardian/expert
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    last_login_at   TIMESTAMPTZ,                           -- 미로그인 시 NULL
    deleted_at      TIMESTAMPTZ                            -- soft delete (NULL=정상)
);