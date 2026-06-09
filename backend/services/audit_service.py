import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from models import AuditLogSensitive, AuditLogGeneral


async def log_sensitive(
    db_audit: AsyncSession,
    user_id,
    action: str,
    resource_type: str,
    resource_id=None,
):
    """
    민감 DB 감사 로그 저장 헬퍼.
    사용 예: await log_sensitive(db_audit, current_user["user_id"], "CREATE", "CONVERSATION", msg.id)
    """
    log = AuditLogSensitive(
        user_id=uuid.UUID(str(user_id)),
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
    )
    db_audit.add(log)


async def log_general(
    db_audit: AsyncSession,
    user_id,
    action: str,
    resource_type: str,
    resource_id=None,
):
    """
    일반 DB 감사 로그 저장 헬퍼.
    사용 예: await log_general(db_audit, new_user.id, "SIGNUP", "USER")
    """
    log = AuditLogGeneral(
        user_id=uuid.UUID(str(user_id)),
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
    )
    db_audit.add(log)
