#  DB 연결 설정
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# 1. 3개의 DB URL 가져오기 (비동기 설정인 +asyncpg 추가)
GENERAL_DB_URL = os.getenv("DATABASE_URL_GENERAL").replace("postgresql://", "postgresql+asyncpg://")
SENSITIVE_DB_URL = os.getenv("DATABASE_URL_SENSITIVE").replace("postgresql://", "postgresql+asyncpg://")
AUDIT_DB_URL = os.getenv("DATABASE_URL_AUDIT").replace("postgresql://", "postgresql+asyncpg://")

# 2. 각각의 엔진 생성
engine_general = create_async_engine(GENERAL_DB_URL, echo=True)
engine_sensitive = create_async_engine(SENSITIVE_DB_URL, echo=True)
engine_audit = create_async_engine(AUDIT_DB_URL, echo=True)

# 3. 세션 메이커 생성
SessionLocalGeneral = sessionmaker(engine_general, class_=AsyncSession, expire_on_commit=False)
SessionLocalSensitive = sessionmaker(engine_sensitive, class_=AsyncSession, expire_on_commit=False)
SessionLocalAudit = sessionmaker(engine_audit, class_=AsyncSession, expire_on_commit=False)

# 4. 의존성 주입용 함수 (FastAPI에서 사용)
async def get_db_general():
    async with SessionLocalGeneral() as session:
        yield session

async def get_db_audit():
    async with SessionLocalAudit() as session:
        yield session