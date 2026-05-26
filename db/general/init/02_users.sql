-- 02_users.sql (수정본)
CREATE TABLE users (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) NOT NULL UNIQUE,
    nickname        VARCHAR(50)  NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    phone_number    VARCHAR(20),
    gender          VARCHAR(20),                          -- 추가: male/female/other/undisclosed (NULL=미응답)
    birth_date      DATE         NOT NULL,                -- 추가: 나이는 여기서 계산 (age 컬럼 두지 않음)
    role            VARCHAR(20)  NOT NULL DEFAULT 'user',
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    last_login_at   TIMESTAMPTZ,
    deleted_at      TIMESTAMPTZ
);