#  DB 연결 설정
import os
from fastapi import HTTPException, Header, Request 
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# 1. 3개의 DB URL 가져오기 (비동기 설정인 +asyncpg 추가)
GENERAL_DB_URL = os.getenv("DATABASE_URL_GENERAL").replace("postgresql://", "postgresql+asyncpg://")
SENSITIVE_DB_URL = os.getenv("DATABASE_URL_SENSITIVE").replace("postgresql://", "postgresql+asyncpg://")
AUDIT_DB_URL = os.getenv("DATABASE_URL_AUDIT").replace("postgresql://", "postgresql+asyncpg://")

# 2. 각각의 엔진 생성
engine_general = create_async_engine(GENERAL_DB_URL,     echo=False)
engine_sensitive = create_async_engine(SENSITIVE_DB_URL, echo=False)
engine_audit = create_async_engine(AUDIT_DB_URL,         echo=False)

# 3. 세션 메이커 생성
SessionLocalGeneral = sessionmaker(engine_general, class_=AsyncSession, expire_on_commit=False)
SessionLocalSensitive = sessionmaker(engine_sensitive, class_=AsyncSession, expire_on_commit=False)
SessionLocalAudit = sessionmaker(engine_audit, class_=AsyncSession, expire_on_commit=False)

# 4. 의존성 주입용 함수 (FastAPI에서 사용)
async def get_db_general(request: Request = None):
    """
    general DB 세션 의존성.

    F-3 일관성: 같은 IP SET 패턴 적용. 현재 general DB엔 audit 트리거 없지만,
    audit_service.log_general()가 직접 INSERT하는 경로에서 향후 IP 활용 가능
    (general audit 트리거 추가 시에도 자동 적용).
    """
    async with SessionLocalGeneral() as session:
        if request and request.client:
            client_ip = request.client.host
            await session.execute(
            text("SELECT set_config('app.client_ip', :ip, false)"),
            {"ip": client_ip}
        )
        yield session

async def get_db_sensitive(request: Request = None):
    """
    sensitive DB 세션 의존성.

    F-3: 매 요청마다 클라이언트 IP를 PostgreSQL 세션 변수에 SET.
    log_to_audit_sensitive() 트리거가 current_setting('app.client_ip', true)로
    이 값을 읽어 audit_logs_sensitive.ip_address 컬럼에 자동 기록.

    request=None 케이스 (백그라운드 태스크, Celery worker, 테스트 등)는
    SET 생략 → 트리거는 NULLIF + missing_ok 패턴으로 NULL 안전 처리.
    """
    async with SessionLocalSensitive() as session:
        if request and request.client:
            client_ip = request.client.host
            await session.execute(
            text("SELECT set_config('app.client_ip', :ip, false)"),
            {"ip": client_ip}
        )
        yield session

async def get_db_audit():
    async with SessionLocalAudit() as session:
        yield session
