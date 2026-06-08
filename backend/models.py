import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Boolean, Float, Text, LargeBinary,
    DateTime, Integer, SmallInteger, Date, ForeignKey
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import declarative_base

# ==========================================
# Base 3개 분리 (DB별로 따로 관리)
# ==========================================
BaseGeneral   = declarative_base()  # 일반 DB (5432)
BaseSensitive = declarative_base()  # 민감 DB (5433)
BaseAudit     = declarative_base()  # 감사 DB (5434)


# ==========================================
# 📘 General DB 테이블들
# ==========================================

class User(BaseGeneral):
    __tablename__ = "users"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email            = Column(String, unique=True, nullable=False)
    nickname         = Column(String, nullable=False)
    hashed_password  = Column(String, nullable=False)
    phone_number     = Column(String, nullable=True)
    role             = Column(String, default="user")
    is_active        = Column(Boolean, default=True)
    gender           = Column(String, nullable=True)   # ← 추가
    birth_date       = Column(Date, nullable=True)     # ← 추가
    created_at       = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_login_at    = Column(DateTime(timezone=True), nullable=True)
    deleted_at       = Column(DateTime(timezone=True), nullable=True)


class Session(BaseGeneral):
    __tablename__ = "sessions"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id       = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    refresh_token = Column(String, unique=True, nullable=False)
    user_agent    = Column(String, nullable=True)
    ip_address    = Column(INET, nullable=True)
    expires_at    = Column(DateTime(timezone=True), nullable=False)
    created_at    = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    revoked_at    = Column(DateTime(timezone=True), nullable=True)


class GuardianConsent(BaseGeneral):
    __tablename__ = "guardian_consents"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id        = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    guardian_phone = Column(String, nullable=False)
    is_active      = Column(Boolean, default=True)
    consented_at   = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    revoked_at     = Column(DateTime(timezone=True), nullable=True)


# ==========================================
# 📕 Sensitive DB 테이블들
# ==========================================

class CategoryCatalog(BaseSensitive):
    __tablename__ = "category_catalog"

    category_code  = Column(String, primary_key=True)
    display_name   = Column(String, nullable=False)
    instrument     = Column(String, nullable=False)
    instrument_ver = Column(String, nullable=True)
    item_count     = Column(SmallInteger, nullable=False)
    max_score      = Column(SmallInteger, nullable=False)
    severity_rule  = Column(JSONB, nullable=True)
    is_active      = Column(Boolean, default=True)


class Classification(BaseSensitive):
    __tablename__ = "classifications"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id             = Column(UUID(as_uuid=True), nullable=False)
    compound_flags      = Column(JSONB, nullable=True)
    selected_prompt_key = Column(String, nullable=True)
    created_at          = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    deleted_at          = Column(DateTime(timezone=True), nullable=True)


class ClassificationResult(BaseSensitive):
    __tablename__ = "classification_results"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    classification_id = Column(UUID(as_uuid=True), ForeignKey("classifications.id"), nullable=False)
    category_code     = Column(String, ForeignKey("category_catalog.category_code"), nullable=False)
    instrument        = Column(String, nullable=False)
    instrument_ver    = Column(String, nullable=True)
    responses         = Column(JSONB, nullable=True)
    total_score       = Column(SmallInteger, nullable=True)
    severity          = Column(String, nullable=True)
    score_delta       = Column(SmallInteger, nullable=True)
    created_at        = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class CounselingSession(BaseSensitive):
    __tablename__ = "counseling_sessions"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id           = Column(UUID(as_uuid=True), nullable=False)
    classification_id = Column(UUID(as_uuid=True), ForeignKey("classifications.id"), nullable=True)
    persona_type      = Column(String, default="empathy")
    started_at        = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    ended_at          = Column(DateTime(timezone=True), nullable=True)
    is_active         = Column(Boolean, default=True)
    deleted_at        = Column(DateTime(timezone=True), nullable=True)


class Conversation(BaseSensitive):
    __tablename__ = "conversations"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id        = Column(UUID(as_uuid=True), ForeignKey("counseling_sessions.id"), nullable=False)
    user_id           = Column(UUID(as_uuid=True), nullable=False)
    role              = Column(String, nullable=False)
    message_type      = Column(String, default="text")
    encrypted_content = Column(LargeBinary, nullable=False)
    encryption_key_id = Column(String, default="none")
    crisis_score      = Column(Float, nullable=True)
    created_at        = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    deleted_at        = Column(DateTime(timezone=True), nullable=True)


class Summary(BaseSensitive):
    __tablename__ = "summaries"

    id                 = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id         = Column(UUID(as_uuid=True), ForeignKey("counseling_sessions.id"), nullable=False)
    user_id            = Column(UUID(as_uuid=True), nullable=False)
    main_complaint     = Column(Text, nullable=True)
    risk_level         = Column(String, default="low")
    suicidal_mentioned = Column(Boolean, default=False)
    core_topics        = Column(JSONB, nullable=True)
    next_session_notes = Column(Text, nullable=True)
    prompt_adjustment  = Column(JSONB, nullable=True)
    created_at         = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    important_memory   = Column(JSONB, nullable=True)


class VoiceFile(BaseSensitive):
    __tablename__ = "voice_files"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id   = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False)
    s3_path           = Column(String, nullable=False)
    encryption_key_id = Column(String, default="none")
    duration_seconds  = Column(Integer, nullable=True)
    retention_until   = Column(Date, nullable=True)
    created_at        = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class CrisisEvent(BaseSensitive):
    __tablename__ = "crisis_events"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id           = Column(UUID(as_uuid=True), nullable=False)
    conversation_id   = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False)
    crisis_score      = Column(Float, nullable=False)
    severity          = Column(String, nullable=False)
    action_taken      = Column(String, nullable=True)
    guardian_notified = Column(Boolean, default=False)
    resolved          = Column(Boolean, default=False)
    occurred_at       = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


# ==========================================
# 📓 Audit DB 테이블들
# ==========================================

class AuditLogGeneral(BaseAudit):
    __tablename__ = "audit_logs_general"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    user_id       = Column(UUID(as_uuid=True), nullable=True)
    action        = Column(String, nullable=False)
    resource_type = Column(String, nullable=False)
    resource_id   = Column(UUID(as_uuid=True), nullable=True)
    ip_address    = Column(INET, nullable=True)
    created_at    = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class AuditLogSensitive(BaseAudit):
    __tablename__ = "audit_logs_sensitive"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    user_id       = Column(UUID(as_uuid=True), nullable=True)
    action        = Column(String, nullable=False)
    resource_type = Column(String, nullable=False)
    resource_id   = Column(UUID(as_uuid=True), nullable=True)
    ip_address    = Column(INET, nullable=True)
    created_at    = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))