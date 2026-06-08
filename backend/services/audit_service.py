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
    log = AuditLogGeneral(
        user_id=uuid.UUID(str(user_id)),
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
    )
    db_audit.add(log)