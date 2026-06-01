from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import bcrypt
from database import get_db_general, get_db_audit
from models import User, AuditLogGeneral
from sqlalchemy.future import select
from datetime import datetime, timezone, timedelta, date  # ← date 추가
from jose import jwt
from typing import Optional
import os

router = APIRouter(prefix="/auth", tags=["Auth"])

# ==========================================
# JWT 설정 (.env에서 읽어옴)
# ==========================================
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

def create_access_token(user_id: str, role: str) -> str:
    payload = {
        "user_id": user_id,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_access_token(token: str) -> dict:
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
    gender: Optional[str] = None
    birth_date: Optional[date] = None  # ← str → date 로 변경

@router.post("/signup")
async def signup(
    user_data: SignupRequest, 
    db_general: AsyncSession = Depends(get_db_general),
    db_audit: AsyncSession = Depends(get_db_audit)
):
    existing_email = await db_general.execute(select(User).where(User.email == user_data.email))
    if existing_email.scalar():
        raise HTTPException(status_code=409, detail="email_taken")

    existing_phone = await db_general.execute(select(User).where(User.phone_number == user_data.phone_number))
    if existing_phone.scalar():
        raise HTTPException(status_code=409, detail="phone_taken")

    try:
        hashed_pw = bcrypt.hashpw(user_data.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        new_user = User(
            email=user_data.email,
            nickname=user_data.nickname,
            hashed_password=hashed_pw,
            phone_number=user_data.phone_number,
            role=user_data.role,
            gender=user_data.gender,
            birth_date=user_data.birth_date
        )
        db_general.add(new_user)
        await db_general.flush()

        audit_log = AuditLogGeneral(
            user_id=new_user.id,
            action="SIGNUP",
            resource_type="USER"
        )
        db_audit.add(audit_log)
        await db_audit.flush()

        await db_general.commit()
        await db_audit.commit()

        access_token = create_access_token(str(new_user.id), new_user.role)
        return {
            "id": str(new_user.id),
            "email": new_user.email,
            "nickname": new_user.nickname,
            "role": new_user.role,
            "needs_guardian_link": False,
            "access_token": access_token
        }

    except Exception as e:
        await db_general.rollback()
        await db_audit.rollback()
        raise HTTPException(status_code=400, detail=str(e))


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
        result = await db_general.execute(select(User).where(User.email == login_data.email))
        user = result.scalar()

        if (not user
            or user.deleted_at is not None
            or not bcrypt.checkpw(login_data.password.encode("utf-8"), user.hashed_password.encode("utf-8"))
            or user.role != login_data.role):
            raise HTTPException(status_code=401, detail="이메일, 비밀번호, 또는 역할이 올바르지 않아요")

        user.last_login_at = datetime.now(timezone.utc)

        audit_log = AuditLogGeneral(
            user_id=user.id,
            action="LOGIN",
            resource_type="USER"
        )
        db_audit.add(audit_log)

        await db_general.commit()
        await db_audit.commit()

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
        raise
    except Exception:
        await db_general.rollback()
        await db_audit.rollback()
        raise HTTPException(status_code=500, detail="로그인 처리 중 서버 오류가 발생했습니다.")