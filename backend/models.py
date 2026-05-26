# DB 테이블 정의

from sqlalchemy import Column, String, Boolean, DateTime, Date, Text, Integer, Float, func, BigInteger, SmallInteger
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()

# =============================================
# 📘 일반 DB (General DB) - 3개 테이블
# =============================================

class User(Base):
    """회원 기본 정보"""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    nickname = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    phone_number = Column(String, unique=True, nullable=False)
    # 가입 시점엔 NULL → 1차 설문 진입 직전 UPDATE
    # NOT NULL 강제는 DB가 아닌 앱 레벨(설문 라우터 가드)에서 처리
    birth_date = Column(Date, nullable=True)        # 생년월일
    gender = Column(String, nullable=True)          # 성별
    role = Column(String, default="user")           # user / guardian / admin
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # 소프트 삭제


class Session(Base):
    """JWT Refresh Token 관리"""
    __tablename__ = "sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)  # 논리적 FK → users.id
    refresh_token = Column(String, nullable=False, unique=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    revoked_at = Column(DateTime(timezone=True), nullable=True)  # 로그아웃 시 기록


class GuardianConsent(Base):
    """보호자 알림 동의 이력"""
    __tablename__ = "guardian_consents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)      # 논리적 FK → users.id (환자)
    guardian_id = Column(UUID(as_uuid=True), nullable=False)  # 논리적 FK → users.id (보호자)
    consented = Column(Boolean, default=False)
    consented_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# =============================================
# 🔒 민감 DB (Sensitive DB) - 8개 테이블
# =============================================
# 이 DB의 모든 user_id는 일반 DB의 users.id를 가리키지만
# PostgreSQL은 다른 DB 간 FK를 지원하지 않으므로 논리적 FK로만 관리
# 정합성은 FastAPI 앱 레벨에서 보장

class CategoryCatalog(Base):
    """분류 카테고리 정의 (우울·불안·불면·노인우울 등)"""
    __tablename__ = "category_catalog"

    category_code = Column(String, primary_key=True)            # 카테고리 코드 (예: PHQ9, GAD7)
    display_name = Column(String, nullable=False)               # 표시명 (예: 우울, 불안)
    instrument = Column(String, nullable=True)                  # 측정 도구명 (예: PHQ-9)
    instrument_ver = Column(String, nullable=True)              # 버전
    item_count = Column(SmallInteger, nullable=True)            # 문항 수
    max_score = Column(SmallInteger, nullable=True)             # 최대 점수
    severity_rule = Column(JSONB, nullable=True)                # 점수 구간별 심각도 규칙
    is_active = Column(Boolean, default=True)                   # 활성 여부


class Classification(Base):
    """초기 상태 분류 세션 (사용자 전체 분류 결과)"""
    __tablename__ = "classifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)        # 논리적 FK → users.id
    compound_flags = Column(JSONB, nullable=True)               # 복합 위험 플래그 (예: {"depression": true, "anxiety": true})
    selected_prompt_key = Column(String, nullable=True)         # 결정된 프롬프트 전략 키 (예: high_risk_watch)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True) # 소프트 삭제


class ClassificationResult(Base):
    """카테고리별 세부 분류 결과 (PHQ-9, GAD-7 등)"""
    __tablename__ = "classification_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    classification_id = Column(UUID(as_uuid=True), nullable=False)  # FK → classifications.id
    category_code = Column(String, nullable=False)                  # FK → category_catalog.category_code
    instrument = Column(String, nullable=True)                      # 측정 도구명 (예: PHQ-9)
    instrument_ver = Column(String, nullable=True)                  # 버전
    responses = Column(JSONB, nullable=True)                        # 문항별 응답 원본
    total_score = Column(SmallInteger, nullable=True)               # 총점
    severity = Column(String, nullable=True)                        # 심각도 (minimal / mild / moderate / severe)
    score_delta = Column(SmallInteger, nullable=True)               # 이전 분류 대비 점수 변화량
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CounselingSession(Base):
    """AI 상담 세션"""
    __tablename__ = "counseling_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)            # 논리적 FK → users.id
    classification_id = Column(UUID(as_uuid=True), nullable=True)   # FK → classifications.id
    persona_type = Column(String, nullable=True)                    # AI 페르소나 (empathy / coaching / neutral)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)     # 소프트 삭제


class Conversation(Base):
    """대화 메시지 (암호화 저장)"""
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), nullable=False)         # FK → counseling_sessions.id
    user_id = Column(UUID(as_uuid=True), nullable=False)            # 논리적 FK → users.id
    role = Column(String, nullable=False)                           # 발화자 (user / assistant)
    message_type = Column(String, nullable=False)                   # 메시지 유형 (text / system / crisis / summary)
    encrypted_content = Column(Text, nullable=False)                # 암호화된 메시지 본문 (1차: 평문 저장)
    encryption_key_id = Column(String, nullable=False)              # 복호화에 사용할 키 ID (1차: "none")
    crisis_score = Column(Float, nullable=True)                     # 위기 점수 (0.0 ~ 1.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)     # 소프트 삭제


class Summary(Base):
    """세션 종료 후 상담 요약"""
    __tablename__ = "summaries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), nullable=False)         # FK → counseling_sessions.id
    user_id = Column(UUID(as_uuid=True), nullable=False)            # 논리적 FK → users.id
    main_complaint = Column(Text, nullable=True)                    # 주요 호소 내용
    risk_level = Column(String, nullable=True)                      # 위험도 (low / medium / high)
    suicidal_mentioned = Column(Boolean, default=False)             # 자살 언급 여부
    core_topics = Column(Text, nullable=True)                       # 핵심 주제
    next_session_notes = Column(Text, nullable=True)                # 다음 세션 참고 메모
    prompt_adjustment = Column(String, nullable=True)               # 다음 세션 프롬프트 조정 방향
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CrisisEvent(Base):
    """위기 감지 이벤트"""
    __tablename__ = "crisis_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)            # 논리적 FK → users.id
    conversation_id = Column(UUID(as_uuid=True), nullable=False)    # FK → conversations.id
    crisis_score = Column(Float, nullable=False)                    # 위기 점수
    severity = Column(String, nullable=False)                       # 심각도 (info / warning / crisis)
    action_taken = Column(String, nullable=True)                    # 취해진 조치
    guardian_notified = Column(Boolean, default=False)              # 보호자 알림 여부
    resolved = Column(Boolean, default=False)                       # 해소 여부
    occurred_at = Column(DateTime(timezone=True), server_default=func.now())


class VoiceFile(Base):
    """음성 입력 파일 (S3 저장, 보존 기한 관리)"""
    __tablename__ = "voice_files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), nullable=False)    # FK → conversations.id
    s3_path = Column(String, nullable=False)                        # S3 저장 경로
    encryption_key_id = Column(String, nullable=False)              # 암호화 키 ID
    duration_seconds = Column(Integer, nullable=True)               # 음성 길이 (초)
    retention_until = Column(Date, nullable=True)                   # 자동 삭제 기한
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# =============================================
# 📓 감사 DB (Audit DB) - 2개 테이블
# =============================================

class AuditLogGeneral(Base):
    """일반 DB 접근/변경 감사 로그"""
    __tablename__ = "audit_logs_general"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), nullable=False)    # 논리적 FK → users.id
    action = Column(String, nullable=False)                 # SIGNUP / LOGIN / UPDATE / DELETE
    resource_type = Column(String, nullable=False)          # USER / SESSION / CONSENT
    resource_id = Column(UUID(as_uuid=True), nullable=True) # 변경된 리소스 ID
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AuditLogSensitive(Base):
    """민감 DB 접근/변경 감사 로그"""
    __tablename__ = "audit_logs_sensitive"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), nullable=False)    # 논리적 FK → users.id
    action = Column(String, nullable=False)                 # CREATE / READ / UPDATE / DELETE
    resource_type = Column(String, nullable=False)          # CLASSIFICATION / SESSION / CONVERSATION / SUMMARY
    resource_id = Column(UUID(as_uuid=True), nullable=True) # 접근한 리소스 ID
    created_at = Column(DateTime(timezone=True), server_default=func.now())