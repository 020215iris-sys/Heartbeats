from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db_general, get_db_audit
from models import User, AuditLogGeneral
from sqlalchemy.future import select
from datetime import datetime, timezone

# 이미 prefix="/auth"가 있으므로 아래 라우터들은 "/signup"만 적어도 "/auth/signup"이 됩니다.
router = APIRouter(prefix="/auth", tags=["Auth"])

# 프론트에서 넘어오는 데이터 규격
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
    db_audit: AsyncSession = Depends(get_db_audit) # 감사 DB 연결 추가
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
        hashed_pw = generate_password_hash(user_data.password)
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

        # 6. 리턴 값에 access_token 추가 (프론트 요청 사항)
        return {
            "id": str(new_user.id),
            "email": new_user.email,
            "nickname": new_user.nickname,
            "role": new_user.role,
            "needs_guardian_link": False,
            "access_token": "임시토큰입니다_추후JWT구현"  # 프론트가 기다리는 토큰!
        }

    except Exception as e:
        # 7. 둘 중 하나라도 오류가 나면 완벽하게 취소 (Rollback)
        await db_general.rollback()
        await db_audit.rollback()
        raise HTTPException(status_code=400, detail="회원가입 처리 중 오류가 발생했습니다.")
    
# 프론트에서 넘어오는 로그인 데이터 규격 [cite: 2124]
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
            or not check_password_hash(user.hashed_password, login_data.password) 
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

        # 6. 성공 결과 반환 (프론트가 기다리는 토큰 및 사용자 정보 포함) 
        return {
            "id": str(user.id),
            "email": user.email,
            "nickname": user.nickname,
            "role": user.role,
            "needs_guardian_link": False,
            "access_token": "임시토큰입니다_추후JWT구현"  # 프론트 로그인 유지를 위한 임시 토큰
        }

    except HTTPException:
        # 401 에러는 바로 던지기
        raise
    except Exception as e:
        # 그 외 DB 오류 등이 나면 롤백
        await db_general.rollback()
        await db_audit.rollback()
        raise HTTPException(status_code=500, detail="로그인 처리 중 서버 오류가 발생했습니다.")