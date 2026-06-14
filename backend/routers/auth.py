from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import bcrypt
from database import get_db_general, get_db_audit
from models import User, AuditLogGeneral, Session, CounselingSession, GuardianInvite
from sqlalchemy import delete
from sqlalchemy.future import select
from datetime import datetime, timezone, timedelta, date
from core.security import verify_access_token, SECRET_KEY, ALGORITHM
from jose import jwt
from typing import Optional
import secrets
import uuid
from tasks.summary import summarize_latest_active_session

router = APIRouter(prefix="/auth", tags=["Auth"])
ALLOWED_SIGNUP_ROLES = {"user", "guardian"}

# ==========================================
# JWT 설정
# ==========================================
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_HOURS = 24

def create_access_token(user_id: str, role: str, nickname: str = "") -> str:
    payload = {
        "user_id": user_id,
        "role": role,
        "nickname": nickname, 
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token() -> str:
    return secrets.token_urlsafe(64)


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
    birth_date: Optional[date] = None
    invite_code: Optional[str] = None 

@router.post("/signup")
async def signup(
    request: Request,
    user_data: SignupRequest,
    db_general: AsyncSession = Depends(get_db_general),
    db_audit: AsyncSession = Depends(get_db_audit)
):
    if user_data.role not in ALLOWED_SIGNUP_ROLES:
        raise HTTPException(status_code=400, detail="허용되지 않은 role입니다.")

    existing_email = await db_general.execute(select(User).where(User.email == user_data.email))
    if existing_email.scalar():
        raise HTTPException(status_code=409, detail="email_taken")

    existing_phone = await db_general.execute(select(User).where(User.phone_number == user_data.phone_number))
    if existing_phone.scalar():
        raise HTTPException(status_code=409, detail="phone_taken")

    # 보호자 가입 게이트키퍼: 유효한 초대코드(pending·미만료)로만 guardian 가입 가능
    invite = None
    if user_data.role == "guardian":
        if not user_data.invite_code:
            raise HTTPException(status_code=400, detail="invite_code_required")
        invite = (await db_general.execute(
            select(GuardianInvite).where(
                GuardianInvite.code == user_data.invite_code,
                GuardianInvite.status == "pending",
                GuardianInvite.expires_at > datetime.now(timezone.utc),
            )
        )).scalar_one_or_none()
        if invite is None:
            raise HTTPException(status_code=400, detail="invalid_or_expired_code")

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

        # 초대코드 연결 확정 (한 트랜잭션): pending → accepted + guardian 지정
        if invite is not None:
            invite.guardian_user_id = new_user.id
            invite.status = "accepted"
            invite.accepted_at = datetime.now(timezone.utc)
            # 그 피보호자의 죽은 코드 청소 (revoked/expired만, accepted는 보존 — N:N)
            await db_general.execute(
                delete(GuardianInvite).where(
                    GuardianInvite.ward_user_id == invite.ward_user_id,
                    GuardianInvite.status.in_(["revoked", "expired"]),
                )
            )

        refresh_token = create_refresh_token()
        
        new_session = Session(
            user_id=new_user.id,
            refresh_token=refresh_token,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=REFRESH_TOKEN_EXPIRE_HOURS)
        )
        db_general.add(new_session)

        audit_log = AuditLogGeneral(
            user_id=new_user.id,
            action="SIGNUP",
            resource_type="USER"
        )
        db_audit.add(audit_log)
        await db_audit.flush()

        await db_general.commit()
        await db_audit.commit()

        access_token = create_access_token(str(new_user.id), new_user.role, new_user.nickname)
        return {
            "id": str(new_user.id),
            "email": new_user.email,
            "nickname": new_user.nickname,
            "role": new_user.role,
            "needs_guardian_link": False,
            "access_token": access_token,
            "refresh_token": refresh_token
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
    request: Request,
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

        refresh_token = create_refresh_token()
        new_session = Session(
            user_id=user.id,
            refresh_token=refresh_token,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=REFRESH_TOKEN_EXPIRE_HOURS)
        )
        db_general.add(new_session)

        audit_log = AuditLogGeneral(
            user_id=user.id,
            action="LOGIN",
            resource_type="USER"
        )
        db_audit.add(audit_log)

        await db_general.commit()
        await db_audit.commit()

        access_token = create_access_token(str(user.id), user.role, user.nickname)
        return {
            "id": str(user.id),
            "email": user.email,
            "nickname": user.nickname,
            "role": user.role,
            "needs_guardian_link": False,
            "access_token": access_token,
            "refresh_token": refresh_token
        }

    except HTTPException:
        raise
    except Exception:
        await db_general.rollback()
        await db_audit.rollback()
        raise HTTPException(status_code=500, detail="로그인 처리 중 서버 오류가 발생했습니다.")


# ==========================================
# Access Token 재발급
# ==========================================
class RefreshRequest(BaseModel):
    refresh_token: str

@router.post("/refresh")
async def refresh(
    body: RefreshRequest,
    db_general: AsyncSession = Depends(get_db_general)
):
    result = await db_general.execute(
        select(Session).where(
            Session.refresh_token == body.refresh_token,
            Session.revoked_at == None,
            Session.expires_at > datetime.now(timezone.utc)
        )
    )
    session = result.scalar()

    if not session:
        raise HTTPException(status_code=401, detail="유효하지 않거나 만료된 refresh_token입니다.")

    user_result = await db_general.execute(select(User).where(User.id == session.user_id))
    user = user_result.scalar()

    if not user or user.deleted_at is not None:
        raise HTTPException(status_code=401, detail="사용자를 찾을 수 없습니다.")

    access_token = create_access_token(str(user.id), user.role, user.nickname)
    return {"access_token": access_token}


# ==========================================
# 로그아웃
# ==========================================
class LogoutRequest(BaseModel):
    refresh_token: str


@router.post("/logout")
async def logout(
    request: Request,
    body: LogoutRequest,
    db_general: AsyncSession = Depends(get_db_general),
    db_audit: AsyncSession = Depends(get_db_audit),
):
    result = await db_general.execute(
        select(Session).where(
            Session.refresh_token == body.refresh_token,
            Session.revoked_at == None
        )
    )
    session = result.scalar()

    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")

    # 진행 중인 상담 세션 요약은 응답 후 백그라운드에서 처리
    summarize_latest_active_session.delay(str(session.user_id))

    # refresh_token revoke
    session.revoked_at = datetime.now(timezone.utc)

    # 감사 로그: 로그인-로그아웃 짝 맞추기. ip_address는 Session 테이블과 동일 소스(request.client.host).
    db_audit.add(AuditLogGeneral(
        user_id=session.user_id,
        action="LOGOUT",
        resource_type="SESSION",
        resource_id=session.id,
        ip_address=request.client.host,
    ))

    await db_general.commit()
    await db_audit.commit()

    return {"message": "로그아웃 되었습니다."}