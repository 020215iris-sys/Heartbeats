-- ============================================================
-- 민감 DB — voice_files 테이블
-- 역할: 음성 입력/출력 파일 메타 정보 (실제 파일은 S3 등 객체 스토리지)
-- 설계 의도:
--   - 음성 파일 자체는 DB 아닌 S3에 (DB는 파일 저장에 부적합)
--   - s3_path: 객체 스토리지 위치 식별자
--   - retention_until: 자동 삭제 일자 (개인정보 보호법 보존 기간 준수)
--   - 한 대화 메시지(conversations)에 음성 파일이 따라붙는 구조
-- ============================================================

CREATE TABLE voice_files (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id     UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    s3_path             VARCHAR(500) NOT NULL,   -- 예: s3://bucket/voice/2026/05/uuid.wav
    encryption_key_id   VARCHAR(50) NOT NULL,    -- 음성 파일도 암호화 저장
    duration_seconds    INTEGER,                 -- 음성 길이
    retention_until     DATE NOT NULL,           -- 보존 만료일 (이 날짜 후 자동 삭제)
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 정기 청소 작업용 (Celery beat이 retention_until 지난 파일 찾아 삭제)
CREATE INDEX idx_voice_retention ON voice_files(retention_until);
-- 한 대화의 음성 파일들 조회
CREATE INDEX idx_voice_conversation ON voice_files(conversation_id);
