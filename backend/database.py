#  DB 연결 설정
import os
from fastapi import HTTPException, Header
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
# ⚠️ 이 함수는 classifications 라우터에서 아래처럼 사용하세요:
#
# from database import require_profile_complete
# from routers.auth import verify_access_token
#
# @router.post("/classifications/start")
# async def start_classification(
#     authorization: str = Header(...),
#     _: None = Depends(require_profile_complete),
#     db_general: AsyncSession = Depends(get_db_general),
# ):
#     token = authorization.replace("Bearer ", "")
#     current_user = verify_access_token(token)
#     ...

async def require_profile_complete(
    authorization: str = Header(...),
    db_general: AsyncSession = get_db_general()  # 세션 직접 주입 안 됨 → 라우터에서 처리 권장
):
    """
    1차 설문 진입 전 birth_date · gender 필수 입력 검사.
    둘 중 하나라도 NULL이면 400 반환.
    DB에는 nullable로 두고 앱 레벨에서 강제하는 패턴.
    """
    from core.security import verify_access_token
    from models import User
    from sqlalchemy.future import select

    token = authorization.replace("Bearer ", "")
    payload = verify_access_token(token)

    async with SessionLocalGeneral() as session:
        result = await session.execute(
            select(User).where(User.id == payload["user_id"])
        )
        user = result.scalar()

    if not user or user.birth_date is None or user.gender is None:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "PROFILE_INCOMPLETE",
                "message": "설문을 시작하기 전에 생년월일과 성별을 입력해야 합니다.",
                "missing_fields": [
                    field for field, value in {
                        "birth_date": user.birth_date if user else None,
                        "gender": user.gender if user else None,
                    }.items() if value is None
                ],
            }
        )