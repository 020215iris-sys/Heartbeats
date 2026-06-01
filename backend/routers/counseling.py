from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
from database import get_db_sensitive, get_db_audit
from models import CounselingSession, Conversation, CrisisEvent, AuditLogSensitive, Summary
from sqlalchemy.future import select
from datetime import datetime, timezone
from routers.auth import verify_access_token
from openai import OpenAI
import uuid
import json
import os
import yaml

from summary_service import request_summary

router = APIRouter(prefix="/counseling", tags=["Counseling"])

# Groq 클라이언트 (요약용 임시)
groq_client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)


# ==========================================
# 현재 유저 가져오는 공통 함수
# ==========================================
def get_current_user(authorization: str = Header(...)) -> dict:
    """헤더에서 JWT 토큰 꺼내서 검증"""
    token = authorization.replace("Bearer ", "")
    return verify_access_token(token)


# ==========================================
# 상담 세션 시작
# ==========================================
class StartSessionRequest(BaseModel):
    classification_id: Optional[str] = None
    persona_type: Optional[str] = "empathy"  # empathy / coaching / neutral


@router.post("/sessions")
async def start_session(
    body: StartSessionRequest,
    current_user: dict = Depends(get_current_user),
    db_sensitive: AsyncSession = Depends(get_db_sensitive),
    db_audit: AsyncSession = Depends(get_db_audit)
):
    """상담 세션 시작 → counseling_sessions 테이블에 행 생성"""
    try:
        new_session = CounselingSession(
            user_id=uuid.UUID(current_user["user_id"]),
            classification_id=uuid.UUID(body.classification_id) if body.classification_id else None,
            persona_type=body.persona_type,
            is_active=True
        )
        db_sensitive.add(new_session)
        await db_sensitive.flush()

        audit_log = AuditLogSensitive(
            user_id=uuid.UUID(current_user["user_id"]),
            action="CREATE",
            resource_type="COUNSELING_SESSION",
            resource_id=new_session.id
        )
        db_audit.add(audit_log)

        await db_sensitive.commit()
        await db_audit.commit()

        return {
            "session_id": str(new_session.id),
            "user_id": str(new_session.user_id),
            "persona_type": new_session.persona_type,
            "started_at": new_session.started_at.isoformat(),
            "is_active": new_session.is_active
        }

    except Exception as e:
        await db_sensitive.rollback()
        await db_audit.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# 상담 세션 조회
# ==========================================
@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db_sensitive: AsyncSession = Depends(get_db_sensitive),
    db_audit: AsyncSession = Depends(get_db_audit)
):
    """session_id로 상담 세션 정보 조회"""
    result = await db_sensitive.execute(
        select(CounselingSession).where(
            CounselingSession.id == uuid.UUID(session_id),
            CounselingSession.deleted_at == None
        )
    )
    session = result.scalar()

    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
    if str(session.user_id) != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="접근 권한이 없습니다.")

    audit_log = AuditLogSensitive(
        user_id=uuid.UUID(current_user["user_id"]),
        action="READ",
        resource_type="COUNSELING_SESSION",
        resource_id=session.id
    )
    db_audit.add(audit_log)
    await db_audit.commit()

    return {
        "session_id": str(session.id),
        "user_id": str(session.user_id),
        "classification_id": str(session.classification_id) if session.classification_id else None,
        "persona_type": session.persona_type,
        "started_at": session.started_at.isoformat(),
        "ended_at": session.ended_at.isoformat() if session.ended_at else None,
        "is_active": session.is_active
    }


# ==========================================
# 대화 메시지 저장
# ==========================================
CRISIS_THRESHOLD = 0.7  # 위기 임계치

class SaveMessageRequest(BaseModel):
    role: str                                  # "user" or "assistant"
    message_type: Optional[str] = "text"       # text / system / crisis / summary
    encrypted_content: str                     # 1차: 평문 저장 / 추후 AES-256 암호화
    crisis_score: Optional[float] = None       # AI가 분석한 위기 점수 (0.0~1.0)


@router.post("/sessions/{session_id}/messages")
async def save_message(
    session_id: str,
    body: SaveMessageRequest,
    current_user: dict = Depends(get_current_user),
    db_sensitive: AsyncSession = Depends(get_db_sensitive),
    db_audit: AsyncSession = Depends(get_db_audit)
):
    """대화 메시지 저장 → conversations 테이블에 행 생성"""
    try:
        result = await db_sensitive.execute(
            select(CounselingSession).where(
                CounselingSession.id == uuid.UUID(session_id),
                CounselingSession.deleted_at == None
            )
        )
        session = result.scalar()
        if not session:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
        if str(session.user_id) != current_user["user_id"]:
            raise HTTPException(status_code=403, detail="접근 권한이 없습니다.")

        new_message = Conversation(
            session_id=uuid.UUID(session_id),
            user_id=uuid.UUID(current_user["user_id"]),
            role=body.role,
            message_type=body.message_type,
            encrypted_content=body.encrypted_content,
            encryption_key_id="none",
            crisis_score=body.crisis_score
        )
        db_sensitive.add(new_message)
        await db_sensitive.flush()

        if body.crisis_score and body.crisis_score >= CRISIS_THRESHOLD:
            crisis_event = CrisisEvent(
                user_id=uuid.UUID(current_user["user_id"]),
                conversation_id=new_message.id,
                crisis_score=body.crisis_score,
                severity="crisis" if body.crisis_score >= 0.9 else "warning",
                guardian_notified=False,
                resolved=False
            )
            db_sensitive.add(crisis_event)

        audit_log = AuditLogSensitive(
            user_id=uuid.UUID(current_user["user_id"]),
            action="CREATE",
            resource_type="CONVERSATION",
            resource_id=new_message.id
        )
        db_audit.add(audit_log)

        await db_sensitive.commit()
        await db_audit.commit()

        return {
            "message_id": str(new_message.id),
            "session_id": session_id,
            "role": new_message.role,
            "message_type": new_message.message_type,
            "crisis_score": new_message.crisis_score,
            "created_at": new_message.created_at.isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        await db_sensitive.rollback()
        await db_audit.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# 대화 내역 조회
# ==========================================
@router.get("/sessions/{session_id}/messages")
async def get_messages(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db_sensitive: AsyncSession = Depends(get_db_sensitive),
    db_audit: AsyncSession = Depends(get_db_audit)
):
    """세션의 전체 대화 내역 조회"""
    session_result = await db_sensitive.execute(
        select(CounselingSession).where(
            CounselingSession.id == uuid.UUID(session_id),
            CounselingSession.deleted_at == None
        )
    )
    session = session_result.scalar()
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
    if str(session.user_id) != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="접근 권한이 없습니다.")

    messages_result = await db_sensitive.execute(
        select(Conversation).where(
            Conversation.session_id == uuid.UUID(session_id),
            Conversation.deleted_at == None
        ).order_by(Conversation.created_at.asc())
    )
    messages = messages_result.scalars().all()

    audit_log = AuditLogSensitive(
        user_id=uuid.UUID(current_user["user_id"]),
        action="READ",
        resource_type="CONVERSATION",
        resource_id=uuid.UUID(session_id)
    )
    db_audit.add(audit_log)
    await db_audit.commit()

    return {
        "session_id": session_id,
        "messages": [
            {
                "message_id": str(m.id),
                "role": m.role,
                "message_type": m.message_type,
                "content": m.encrypted_content,
                "crisis_score": m.crisis_score,
                "created_at": m.created_at.isoformat()
            }
            for m in messages
        ]
    }


# ==========================================
# 상담 종료 + 요약 생성
# ==========================================
@router.patch("/sessions/{session_id}/end")
async def end_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db_sensitive: AsyncSession = Depends(get_db_sensitive),
    db_audit: AsyncSession = Depends(get_db_audit)
):
    """상담 종료 → ended_at 업데이트 + LoRA 요약 생성 + summaries 저장"""
    try:
        result = await db_sensitive.execute(
            select(CounselingSession).where(
                CounselingSession.id == uuid.UUID(session_id),
                CounselingSession.deleted_at == None
            )
        )
        session = result.scalar()
        if not session:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
        if str(session.user_id) != current_user["user_id"]:
            raise HTTPException(status_code=403, detail="접근 권한이 없습니다.")

        session.ended_at = datetime.now(timezone.utc)
        session.is_active = False

        messages_result = await db_sensitive.execute(
            select(Conversation).where(
                Conversation.session_id == uuid.UUID(session_id),
                Conversation.deleted_at == None
            ).order_by(Conversation.created_at.asc())
        )
        messages = messages_result.scalars().all()

        transcript = "\n".join([
            f"{'내담자' if m.role == 'user' else '상담사'}: {m.encrypted_content}"
            for m in messages
        ])

        # 5. LoRA summary 요청 → 실패 시 기본값으로 fallback
        try:
            summary_result = request_summary(transcript)
            raw_output = summary_result["output"]

            # yaml 파싱 시도 → 실패하면 텍스트 직접 파싱  ← 수정
            try:
                summary_data = yaml.safe_load(raw_output)
                if not isinstance(summary_data, dict):
                    raise ValueError("yaml 파싱 실패")
            except:
                summary_data = {}
                current_key = None
                items = []
                for line in raw_output.splitlines():
                    line = line.strip()
                    if line.endswith(":") and not line.startswith("-"):
                        if current_key and items:
                            summary_data[current_key] = items
                        current_key = line[:-1]
                        items = []
                    elif line.startswith("-"):
                        items.append(line[1:].strip())
                    elif line and current_key:
                        summary_data[current_key] = line
                        current_key = None
                if current_key and items:
                    summary_data[current_key] = items

            if not isinstance(summary_data, dict):
                summary_data = {}
            summary_data.setdefault("risk_level", "low")
            summary_data.setdefault("suicidal_mentioned", False)

        except Exception:
            summary_data = {
                "main_complaint": "",
                "risk_level": "low",
                "suicidal_mentioned": False,
                "core_topics": [],        # ← 빈 리스트
                "next_session_notes": "",
                "prompt_adjustment": {}   # ← 빈 딕셔너리
            }

        # 6. summaries 테이블에 저장
        new_summary = Summary(
            session_id=uuid.UUID(session_id),
            user_id=uuid.UUID(current_user["user_id"]),
            main_complaint=summary_data.get("main_complaint", ""),
            risk_level=summary_data.get("risk_level", "low"),
            suicidal_mentioned=summary_data.get("suicidal_mentioned", False),
            core_topics=json.loads(summary_data.get("core_topics", "[]")) if isinstance(summary_data.get("core_topics"), str) else summary_data.get("core_topics", []),
            next_session_notes=summary_data.get("next_session_notes", ""),
            prompt_adjustment=json.loads(summary_data.get("prompt_adjustment", "{}")) if isinstance(summary_data.get("prompt_adjustment"), str) else summary_data.get("prompt_adjustment", {})
        )
        db_sensitive.add(new_summary)

        audit_log = AuditLogSensitive(
            user_id=uuid.UUID(current_user["user_id"]),
            action="UPDATE",
            resource_type="COUNSELING_SESSION",
            resource_id=uuid.UUID(session_id)
        )
        db_audit.add(audit_log)

        await db_sensitive.commit()
        await db_audit.commit()

        return {
            "session_id": session_id,
            "ended_at": session.ended_at.isoformat(),
            "is_active": False,
            "summary_id": str(new_summary.id)
        }

    except HTTPException:
        raise
    except Exception as e:
        await db_sensitive.rollback()
        await db_audit.rollback()
        raise HTTPException(status_code=500, detail=str(e))