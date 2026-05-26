#  DB 연결 설정
import os
from fastapi import HTTPException
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

async def get_db_sensitive():
    async with SessionLocalSensitive() as session:
        yield session

async def get_db_audit():
    async with SessionLocalAudit() as session:
        yield session

# 5. 설문 진입 가드
async def require_profile_complete(current_user):
    """
    1차 설문 진입 전 birth_date · gender 필수 입력 검사.
    둘 중 하나라도 NULL이면 400 반환.
    DB에는 nullable로 두고 앱 레벨에서 강제하는 패턴.

    사용법:
        @router.post("/classifications/start")
        async def start_classification(
            current_user: User = Depends(get_current_user),
            _: None = Depends(require_profile_complete),
        ):
    """
    if current_user.birth_date is None or current_user.gender is None:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "PROFILE_INCOMPLETE",
                "message": "설문을 시작하기 전에 생년월일과 성별을 입력해야 합니다.",
                "missing_fields": [
                    field for field, value in {
                        "birth_date": current_user.birth_date,
                        "gender": current_user.gender,
                    }.items() if value is None
                ],
            }
        )