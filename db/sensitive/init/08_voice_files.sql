-- 08_voice_files.sql
-- db_sensitive · VOICE_FILES — 음성 파일 메타데이터
-- 실제 음성 파일은 S3에 저장, DB엔 경로·메타데이터만
-- 의존성: conversations(06)
CREATE TABLE voice_files (
    id                UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id   UUID         NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    s3_path           VARCHAR(512) NOT NULL,         -- S3 객체 경로
    encryption_key_id VARCHAR(50)  NOT NULL,
    duration_seconds  INTEGER,                       -- 재생 길이(초)
    retention_until   DATE,                          -- 보관 만료일(자동 삭제 기준)
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX idx_voice_conversation_id ON voice_files(conversation_id);