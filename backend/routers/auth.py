from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import bcrypt
from database import get_db_general, get_db_audit
from models import User, AuditLogGeneral
from sqlalchemy.future import select
from datetime import datetime, timezone, timedelta
from jose import jwt
import os

# 이미 prefix="/auth"가 있으므로 아래 라우터들은 "/signup"만 적어도 "/auth/signup"이 됩니다.
router = APIRouter(prefix="/auth", tags=["Auth"])

# ==========================================
# JWT 설정 (.env에서 읽어옴)
# ==========================================
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 액세스 토큰 1시간

def create_access_token(user_id: str, role: str) -> str:
    """JWT 액세스 토큰 발급"""
    payload = {
        "user_id": user_id,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_access_token(token: str) -> dict:
    """JWT 토큰 검증 및 payload 반환 (다른 라우터에서 import해서 사용)"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except Exception:
        raise HTTPException(status_code=401, detail="유효하지 않거나 만료된 토큰입니다.")


# ==========================================
# 회원가입
# ==========================================
class SignupRequest(BaseModel):
    email: str
    password: str
    role: str
    nickname: str
    phone_number: str

@router.post("/signup")
async def signup(
    user_data: SignupRequest, 
    db_general: AsyncSession = Depends(get_db_general),
    db_audit: AsyncSession = Depends(get_db_audit)
):
    # 1. 이메일 중복 체크 (프론트 요청: 409 email_taken)
    existing_email = await db_general.execute(select(User).where(User.email == user_data.email))
    if existing_email.scalar():
        raise HTTPException(status_code=409, detail="email_taken")

    # 2. 전화번호 중복 체크 (프론트 요청: 409 phone_taken)
    existing_phone = await db_general.execute(select(User).where(User.phone_number == user_data.phone_number))
    if existing_phone.scalar():
        raise HTTPException(status_code=409, detail="phone_taken")

    try:
        # 3. 비밀번호 해싱 및 User 객체 생성
        hashed_pw = bcrypt.hashpw(user_data.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        new_user = User(
            email=user_data.email,
            nickname=user_data.nickname,
            hashed_password=hashed_pw,
            phone_number=user_data.phone_number,
            role=user_data.role
        )
        db_general.add(new_user)
        # Audit 로그에 넣을 고유 ID(UUID)를 미리 발급받기 위해 flush 실행
        await db_general.flush()

        # 4. 감사 DB에 저장할 로그 객체 생성
        audit_log = AuditLogGeneral(
            user_id=new_user.id,
            action="SIGNUP",
            resource_type="USER"
        )
        db_audit.add(audit_log)
        # 중요: 양쪽 DB 모두 flush하여 커밋 전 상태로 준비
        await db_audit.flush()

        # 5. General DB, Audit DB 순차적 커밋 (Cross-DB 정합성)
        await db_general.commit()
        await db_audit.commit()

        # 6. JWT 발급 후 반환
        access_token = create_access_token(str(new_user.id), new_user.role)
        return {
            "id": str(new_user.id),
            "email": new_user.email,
            "nickname": new_user.nickname,
            "role": new_user.role,
            "needs_guardian_link": False,
            "access_token": access_token
        }

    except Exception:
        # 둘 중 하나라도 오류가 나면 완벽하게 취소 (Rollback)
        await db_general.rollback()
        await db_audit.rollback()
        raise HTTPException(status_code=400, detail="회원가입 처리 중 오류가 발생했습니다.")


# ==========================================
# 로그인
# ==========================================
class LoginRequest(BaseModel):
    email: str
    password: str
    role: str

@router.post("/login")
async def login(
    login_data: LoginRequest, 
    db_general: AsyncSession = Depends(get_db_general),
    db_audit: AsyncSession = Depends(get_db_audit)
):
    try:
        # 1. DB에서 이메일로 사용자 찾기
        result = await db_general.execute(select(User).where(User.email == login_data.email))
        user = result.scalar()

        # 2. 통합 검증 (프론트 요청: 보안상 무엇이 틀렸는지 모르게 401 에러 통일)
        # (유저가 없거나 OR 탈퇴한 유저거나 OR 비밀번호가 안 맞거나 OR 역할이 다를 경우)
        if (not user
            or user.deleted_at is not None
            or not bcrypt.checkpw(login_data.password.encode("utf-8"), user.hashed_password.encode("utf-8"))
            or user.role != login_data.role):
            raise HTTPException(status_code=401, detail="이메일, 비밀번호, 또는 역할이 올바르지 않아요")

        # 3. 로그인 성공: 마지막 로그인 시간(last_login_at) 현재 시간으로 갱신
        user.last_login_at = datetime.now(timezone.utc)

        # 4. 감사 DB(Audit)에 로그인 기록 남기기
        audit_log = AuditLogGeneral(
            user_id=user.id,
            action="LOGIN",
            resource_type="USER"
        )
        db_audit.add(audit_log)

        # 5. General DB, Audit DB 순차적 커밋
        await db_general.commit()
        await db_audit.commit()

        # 6. JWT 발급 후 반환
        access_token = create_access_token(str(user.id), user.role)
        return {
            "id": str(user.id),
            "email": user.email,
            "nickname": user.nickname,
            "role": user.role,
            "needs_guardian_link": False,
            "access_token": access_token
        }

    except HTTPException:
        # 401 에러는 바로 던지기
        raise
    except Exception:
        # 그 외 DB 오류 등이 나면 롤백
        await db_general.rollback()
        await db_audit.rollback()
        raise HTTPException(status_code=500, detail="로그인 처리 중 서버 오류가 발생했습니다.")