"""보호자 연결: 피보호자(ward)가 초대 코드를 발급한다."""

import random
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from ..services import api_client

from database import get_db_general
from core.security import get_current_user
from models import GuardianInvite, User

router = APIRouter(prefix="/guardian", tags=["Guardian"])

INVITE_TTL_MINUTES = 60   # 가입용 토큰이라 짧게 (DB 설계 의도)


async def _generate_unique_code(db: AsyncSession) -> str:
    """8자리 숫자 코드를 유니크하게 생성."""
    for _ in range(10):
        code = f"{random.randint(0, 99_999_999):08d}"
        exists = (await db.execute(
            select(GuardianInvite.id).where(GuardianInvite.code == code)
        )).first()
        if not exists:
            return code
    raise HTTPException(500, "초대 코드 생성 실패. 다시 시도해주세요.")


@router.post("/invite")
async def create_invite(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_general),
):
    """피보호자가 보호자 초대 코드 발급 (status=pending, 1시간 만료)."""
    if current_user.get("role") != "user":
        raise HTTPException(403, "피보호자 계정만 초대 코드를 발급할 수 있습니다.")

    ward_uuid = uuid.UUID(current_user["user_id"])
    
    await db.execute(
        update(GuardianInvite)
        .where(
            GuardianInvite.ward_user_id == ward_uuid,
            GuardianInvite.status == "pending",
        )
        .values(status="revoked", revoked_at=datetime.now(timezone.utc))
    )

    code = await _generate_unique_code(db)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=INVITE_TTL_MINUTES)

    invite = GuardianInvite(
        code=code,
        ward_user_id=ward_uuid,
        status="pending",
        expires_at=expires_at,
    )
    db.add(invite)
    await db.commit()

    return {"code": code, "expires_at": expires_at.isoformat()}

@router.get("/wards")
async def list_wards(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_general),
):
    """보호자가 연결된 피보호자(ward) 목록. status=accepted, 미해제."""
    if current_user.get("role") != "guardian":
        raise HTTPException(403, "보호자 전용입니다.")
    rows = await db.execute(
        select(User.id, User.nickname)
        .join(GuardianInvite, GuardianInvite.ward_user_id == User.id)
        .where(
            GuardianInvite.guardian_user_id == uuid.UUID(current_user["user_id"]),
            GuardianInvite.status == "accepted",
            GuardianInvite.revoked_at.is_(None),
            User.deleted_at.is_(None),
        )
    )
    return {"wards": [{"ward_id": str(wid), "nickname": nick} for wid, nick in rows.all()]}