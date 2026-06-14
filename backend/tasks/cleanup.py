# backend/tasks/cleanup.py
"""
자동삭제·익명화 Celery 태스크.

정책:
- conversations: 3개월 후 soft delete (deleted_at SET)
- summaries: 1년 후 soft delete
- classifications + classification_results: 1년 후 soft delete (동기)
- counseling_sessions: 1년 후 익명화 (user_id, classification_id → NULL)
- crisis_events: 영구 보존 (자동삭제 대상 X)
- voice_files: STT PR로 미룸

스케줄: celery_app.conf.beat_schedule 에서 매일 새벽 3시 (KST) 실행 예정.
수동 실행 (테스트):
    docker compose exec api celery -A celery_app call tasks.cleanup.soft_delete_old_conversations
"""
import asyncio
import os
from datetime import datetime, timezone, timedelta

from sqlalchemy import update
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from celery_app import celery_app
from models import (
    Conversation,
    Summary,
    Classification,
    ClassificationResult,
    CounselingSession,
)


# ──────────────────────────────────────────
# 정책 상수 — 변경 시 여기만 수정
# ──────────────────────────────────────────
CONVERSATIONS_RETENTION_DAYS = 90    # 3개월
SUMMARIES_RETENTION_DAYS = 365       # 1년
CLASSIFICATIONS_RETENTION_DAYS = 365 # 1년
SESSIONS_ANONYMIZE_DAYS = 365        # 1년


# ──────────────────────────────────────────
# DB URL 헬퍼
# ──────────────────────────────────────────
def _async_db_url(env_name: str) -> str:
    value = os.getenv(env_name)
    if not value:
        raise RuntimeError(f"{env_name} 환경변수가 없습니다.")
    return value.replace("postgresql://", "postgresql+asyncpg://")


def _make_session():
    """Worker 안전한 sensitive DB 세션 메이커."""
    engine = create_async_engine(
        _async_db_url("DATABASE_URL_SENSITIVE"),
        poolclass=NullPool,
    )
    SessionMaker = async_sessionmaker(engine, expire_on_commit=False)
    return engine, SessionMaker


# ══════════════════════════════════════════
# 1) conversations 3개월 soft delete
# ══════════════════════════════════════════
@celery_app.task(name="tasks.cleanup.soft_delete_old_conversations")
def soft_delete_old_conversations():
    return asyncio.run(_soft_delete_old_conversations())


async def _soft_delete_old_conversations():
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=CONVERSATIONS_RETENTION_DAYS)

    engine, SessionMaker = _make_session()
    try:
        async with SessionMaker() as db:
            stmt = (
                update(Conversation)
                .where(
                    Conversation.created_at < cutoff,
                    Conversation.deleted_at.is_(None),
                )
                .values(deleted_at=now)
            )
            result = await db.execute(stmt)
            await db.commit()
            return {
                "task": "soft_delete_old_conversations",
                "cutoff": cutoff.isoformat(),
                "deleted_count": result.rowcount,
            }
    finally:
        await engine.dispose()


# ══════════════════════════════════════════
# 2) summaries 1년 soft delete
# ══════════════════════════════════════════
@celery_app.task(name="tasks.cleanup.soft_delete_old_summaries")
def soft_delete_old_summaries():
    return asyncio.run(_soft_delete_old_summaries())


async def _soft_delete_old_summaries():
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=SUMMARIES_RETENTION_DAYS)

    engine, SessionMaker = _make_session()
    try:
        async with SessionMaker() as db:
            stmt = (
                update(Summary)
                .where(
                    Summary.created_at < cutoff,
                    Summary.deleted_at.is_(None),
                )
                .values(deleted_at=now)
            )
            result = await db.execute(stmt)
            await db.commit()
            return {
                "task": "soft_delete_old_summaries",
                "cutoff": cutoff.isoformat(),
                "deleted_count": result.rowcount,
            }
    finally:
        await engine.dispose()


# ══════════════════════════════════════════
# 3) classifications + classification_results 1년 soft delete
# ══════════════════════════════════════════
@celery_app.task(name="tasks.cleanup.soft_delete_old_classifications")
def soft_delete_old_classifications():
    return asyncio.run(_soft_delete_old_classifications())


async def _soft_delete_old_classifications():
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=CLASSIFICATIONS_RETENTION_DAYS)

    engine, SessionMaker = _make_session()
    try:
        async with SessionMaker() as db:
            # parent classifications
            cls_stmt = (
                update(Classification)
                .where(
                    Classification.created_at < cutoff,
                    Classification.deleted_at.is_(None),
                )
                .values(deleted_at=now)
            )
            cls_result = await db.execute(cls_stmt)

            # child classification_results (parent와 동기)
            res_stmt = (
                update(ClassificationResult)
                .where(
                    ClassificationResult.created_at < cutoff,
                    ClassificationResult.deleted_at.is_(None),
                )
                .values(deleted_at=now)
            )
            res_result = await db.execute(res_stmt)

            await db.commit()
            return {
                "task": "soft_delete_old_classifications",
                "cutoff": cutoff.isoformat(),
                "classifications_deleted": cls_result.rowcount,
                "classification_results_deleted": res_result.rowcount,
            }
    finally:
        await engine.dispose()


# ══════════════════════════════════════════
# 4) counseling_sessions 1년 익명화
# ══════════════════════════════════════════
@celery_app.task(name="tasks.cleanup.anonymize_old_counseling_sessions")
def anonymize_old_counseling_sessions():
    return asyncio.run(_anonymize_old_counseling_sessions())


async def _anonymize_old_counseling_sessions():
    """
    1년 지난 회기의 식별 컬럼을 NULL로 마스킹.
    - user_id, classification_id → NULL
    - started_at, ended_at, persona_type 등은 통계용으로 보존
    - 자식(conversations, summaries)은 각자의 정책으로 이미 처리됨
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=SESSIONS_ANONYMIZE_DAYS)

    engine, SessionMaker = _make_session()
    try:
        async with SessionMaker() as db:
            stmt = (
                update(CounselingSession)
                .where(
                    CounselingSession.started_at < cutoff,
                    CounselingSession.user_id.is_not(None),   # 이미 익명화된 행 제외 (멱등)
                )
                .values(
                    user_id=None,
                    classification_id=None,
                )
            )
            result = await db.execute(stmt)
            await db.commit()
            return {
                "task": "anonymize_old_counseling_sessions",
                "cutoff": cutoff.isoformat(),
                "anonymized_count": result.rowcount,
            }
    finally:
        await engine.dispose()