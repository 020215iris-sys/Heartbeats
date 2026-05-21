# 로그인/회원가입 APi 기입 

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from werkzeug.security import generate_password_hash
from database import get_db_general, get_db_audit
from models import User, AuditLogGeneral

router = APIRouter(prefix="/auth", tags=["Auth"])

# 프론트에서 넘어오는 데이터 규격
class SignupRequest(BaseModel):
    email: str
    password: str
    role: str
    nickname: str
    phone_number: str

@router.post("/signup", status_code=201)
async def signup(
    req: SignupRequest, 
    db_general: AsyncSession = Depends(get_db_general),
    db_audit: AsyncSession = Depends(get_db_audit)
):
    # 1. 비밀번호 암호화 ★
    hashed_pw = generate_password_hash(req.password)
    
    # 2. 유저 객체 생성
    new_user = User(
        email=req.email,
        hashed_password=hashed_pw,
        role=req.role,
        nickname=req.nickname,
        phone_number=req.phone_number
    )
    db_general.add(new_user)
    
    try:
        # DB에 밀어넣어서 새 유저의 ID(UUID)를 먼저 발급받음 (commit은 안 한 상태)
        await db_general.flush() 

        # 3. 감사 로그 객체 생성 (방금 발급된 새 유저 ID 사용)
        new_log = AuditLogGeneral(
            user_id=new_user.id,
            action="SIGNUP",
            resource_type="USER"
        )
        db_audit.add(new_log)

        # 4. 두 DB 모두 정상적으로 적용되면 동시 커밋 (Cross-DB 정합성 보장) ★
        # General DB 랑 audit DB 커밋
        await db_general.commit()
        await db_audit.commit()
        
        return {
            "id": str(new_user.id),
            "email": new_user.email,
            "nickname": new_user.nickname,
            "role": new_user.role,
            "needs_guardian_link": False
        }

    except Exception as e:
        # 5. 둘 중 하나라도 뻑나면 전부 취소 (Rollback)
        await db_general.rollback()
        await db_audit.rollback()
        raise HTTPException(status_code=400, detail="회원가입 처리 중 오류가 발생했습니다.")