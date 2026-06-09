# backend/tasks/summary.py
import asyncio
import uuid

from celery_app import celery_app
from database import SessionLocalSensitive, SessionLocalAudit
from models import CounselingSession
from sqlalchemy.future import select


@celery_app.task(name="tasks.summary.summarize_latest_active_session")
def summarize_latest_active_session(user_id: str):
    return asyncio.run(_summarize_latest_active_session(user_id))


async def _summarize_latest_active_session(user_id: str):
    from routers.counseling import close_session_with_summary

    async with SessionLocalSensitive() as db_sensitive, SessionLocalAudit() as db_audit:
        result = await db_sensitive.execute(
            select(CounselingSession)
            .where(
                CounselingSession.user_id == uuid.UUID(user_id),
                CounselingSession.is_active == True,
                CounselingSession.deleted_at == None,
            )
            .order_by(CounselingSession.started_at.desc())
        )

        active_sessions = result.scalars().all()
        if not active_sessions:
            return {"status": "skipped", "reason": "no_active_session"}

        current = active_sessions[0]
        await close_session_with_summary(current, db_sensitive, db_audit)

        for stale in active_sessions[1:]:
            stale.is_active = False
            stale.ended_at = current.ended_at

        await db_sensitive.commit()
        await db_audit.commit()

        return {
            "status": "ok",
            "session_id": str(current.id),
        }