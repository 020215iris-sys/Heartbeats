# backend/tasks/summary.py
import asyncio
import os
import uuid

from dotenv import load_dotenv
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from celery_app import celery_app
from models import CounselingSession

load_dotenv()


def _async_db_url(env_name: str) -> str:
    value = os.getenv(env_name)
    if not value:
        raise RuntimeError(f"{env_name} is not set")
    return value.replace("postgresql://", "postgresql+asyncpg://")


@celery_app.task(name="tasks.summary.summarize_latest_active_session")
def summarize_latest_active_session(user_id: str):
    return asyncio.run(_summarize_latest_active_session(user_id))


async def _summarize_latest_active_session(user_id: str):
    from routers.counseling import close_session_with_summary

    sensitive_engine = create_async_engine(
        _async_db_url("DATABASE_URL_SENSITIVE"),
        echo=True,
        poolclass=NullPool,
    )
    audit_engine = create_async_engine(
        _async_db_url("DATABASE_URL_AUDIT"),
        echo=True,
        poolclass=NullPool,
    )

    SensitiveSession = async_sessionmaker(
        sensitive_engine,
        expire_on_commit=False,
    )
    AuditSession = async_sessionmaker(
        audit_engine,
        expire_on_commit=False,
    )

    try:
        async with SensitiveSession() as db_sensitive, AuditSession() as db_audit:
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

    except Exception:
        try:
            await db_sensitive.rollback()
        except Exception:
            pass
        try:
            await db_audit.rollback()
        except Exception:
            pass
        raise

    finally:
        await sensitive_engine.dispose()
        await audit_engine.dispose()


# ──────────────────────────────────────────
# 특정 session_id 요약 (60분 타임아웃 경로용)
# - chat_service의 동기 요약을 대체. 이미 닫힌 옛 세션 1건만 요약 생성.
# - summarize_latest_active_session 과 달리 '최신 active'를 찾지 않으므로
#   타임아웃 직후 새 세션을 만들어도 레이스가 없다.
# ──────────────────────────────────────────
@celery_app.task(name="tasks.summary.summarize_session")
def summarize_session(session_id: str):
    return asyncio.run(_summarize_session(session_id))


async def _summarize_session(session_id: str):
    from routers.counseling import close_session_with_summary

    sensitive_engine = create_async_engine(
        _async_db_url("DATABASE_URL_SENSITIVE"),
        echo=True,
        poolclass=NullPool,
    )
    audit_engine = create_async_engine(
        _async_db_url("DATABASE_URL_AUDIT"),
        echo=True,
        poolclass=NullPool,
    )

    SensitiveSession = async_sessionmaker(
        sensitive_engine,
        expire_on_commit=False,
    )
    AuditSession = async_sessionmaker(
        audit_engine,
        expire_on_commit=False,
    )

    try:
        async with SensitiveSession() as db_sensitive, AuditSession() as db_audit:
            result = await db_sensitive.execute(
                select(CounselingSession).where(
                    CounselingSession.id == uuid.UUID(session_id),
                    CounselingSession.deleted_at == None,
                )
            )
            session = result.scalar()
            if not session:
                return {"status": "skipped", "reason": "not_found"}

            await close_session_with_summary(session, db_sensitive, db_audit)

            await db_sensitive.commit()
            await db_audit.commit()

            return {
                "status": "ok",
                "session_id": str(session.id),
            }

    except Exception:
        try:
            await db_sensitive.rollback()
        except Exception:
            pass
        try:
            await db_audit.rollback()
        except Exception:
            pass
        raise

    finally:
        await sensitive_engine.dispose()
        await audit_engine.dispose()
