# DB 테이블 정의

from sqlalchemy import Column, String, Boolean, DateTime, func, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()

# 📘 일반 DB용 모델
class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    nickname = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    phone_number = Column(String, unique=True, nullable=False)
    role = Column(String, default="user")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login_at = Column(DateTime(timezone=True), nullable=True)

# 📓 감사 DB용 모델
class AuditLogGeneral(Base):
    __tablename__ = "audit_logs_general"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), nullable=False) # 논리적 FK
    action = Column(String, nullable=False)
    resource_type = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())