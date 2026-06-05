from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
from database import get_db_sensitive, get_db_audit
from models import CounselingSession, Conversation, CrisisEvent, AuditLogSensitive, Summary
from sqlalchemy.future import select
from datetime import datetime, timezone
from core.security import get_current_user
from openai import OpenAI
import uuid
import json
import os
import yaml
from core.crypto import decrypt_content
from summary_service import request_summary

router = APIRouter(prefix="/counseling", tags=["Counseling"])

groq_client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)

# ==========================================
# 세션 종료 + 요약 저장 공통 함수
# ==========================================
async def close_session_with_summary(session, db_sensitive, db_audit):
    """세션 종료 + LoRA 요약 생성 + summaries 저장 (공통 로직)"""
    session.ended_at = datetime.now(timezone.utc)
    session.is_active = False

    messages_result = await db_sensitive.execute(
        select(Conversation).where(
            Conversation.session_id == session.id,
            Conversation.deleted_at == None
        ).order_by(Conversation.created_at.asc())
    )
    messages = messages_result.scalars().all()

    transcript = "\n".join([
        f"{'내담자' if m.role == 'user' else '상담사'}: {decrypt_content(m.encrypted_content, m.encryption_key_id)}"
        for m in messages
    ])

    try:
        summary_result = request_summary(transcript)
        raw_output = summary_result["output"]

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
        # Groq으로 risk_level / suicidal_mentioned 판단
        risk_prompt = f"""당신은 정신건강 상담 요약을 검토하는 분류기입니다.

        주어진 상담 요약을 읽고 다음 두 항목만 판단하세요.

        1. risk_level
        * low
        * medium
        * high

        2. suicidal_mentioned
        * true
        * false

        판단 기준

        low: 일반적인 스트레스, 고민, 갈등 수준. 자살 및 자해 관련 언급 없음
        medium: 우울감, 불안감, 무기력감, 자기비난, 절망감 등이 반복적으로 나타남. 정서적 고통이 크지만 자살 또는 자해 의도는 확인되지 않음
        high: 자살, 자해, 죽고 싶음, 사라지고 싶음, 삶에 지속 의지를 부정하는 표현, 극단적 선택 등 위험 표현이 존재함

        규칙
        * 자살 또는 자해 관련 표현이 있으면 suicidal_mentioned=true
        * suicidal_mentioned=true 이면 risk_level=high
        * 반드시 JSON만 출력
        * 설명 금지
        * reason 출력 금지

        상담 요약:
        main_complaint: {summary_data.get("main_complaint", "")}
        core_topics: {summary_data.get("core_topics", [])}
        next_session_notes: {summary_data.get("next_session_notes", "")}
        prompt_adjustment: {summary_data.get("prompt_adjustment", {})}"""
        

        # ── 위험도 분류는 "독립 try"로 분리한다 ──────────────────────────
        # 이 블록 안에서 Groq 호출이나 json 파싱이 실패해도, 바깥 try로
        # 예외가 새어나가지 않으므로 위에서 만든 요약(summary_data)이 보존된다.

        # 1) 기본값을 먼저 넣어둔다.
        #    아래가 실패하면 risk 필드만 이 기본값(low/False)으로 남는다.
        summary_data.setdefault("risk_level", "low")
        summary_data.setdefault("suicidal_mentioned", False)

        try:
            # 2) Groq에 위험도 판단 요청
            risk_response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": risk_prompt}]
            )

            risk_text = risk_response.choices[0].message.content.strip()

            # 4) 모델이 ```json ... ``` 코드펜스로 감싸 주는 경우 방어
            #    (지금 char 0 에러의 유력한 원인. 펜스/json 라벨 제거 후 파싱)
            if risk_text.startswith("```"):
                risk_text = risk_text.strip("`").strip()
                if risk_text[:4].lower() == "json":
                    risk_text = risk_text[4:].strip()

            # 5) 빈 문자열이면 json.loads가 터지므로 건너뛰고 기본값을 유지
            if risk_text:
                risk_parsed = json.loads(risk_text)
                summary_data["risk_level"] = risk_parsed.get("risk_level", "low")
                summary_data["suicidal_mentioned"] = risk_parsed.get("suicidal_mentioned", False)

        except Exception as e:
            # 위험도 분류 실패 → risk는 기본값(low/False) 유지, 요약 본문은 보존
            pass

    except Exception:
            # 요약 생성/파싱 자체가 실패하면 빈 요약으로 저장(흐름 중단 방지)
            summary_data = {
                "main_complaint": "",
                "risk_level": "low",
                "suicidal_mentioned": False,
                "core_topics": [],
                "next_session_notes": "",
                "prompt_adjustment": {}
            }

    new_summary = Summary(
        session_id=session.id,
        user_id=session.user_id,
        main_complaint=summary_data.get("main_complaint", ""),
        risk_level=summary_data.get("risk_level", "low"),
        suicidal_mentioned=summary_data.get("suicidal_mentioned", False),
        core_topics=summary_data.get("core_topics", []),
        prompt_adjustment=summary_data.get("prompt_adjustment", {}),    
        next_session_notes=summary_data.get("next_session_notes", ""),
        )
    db_sensitive.add(new_summary)
    await db_sensitive.flush()
    return new_summary


# ==========================================
# 상담 세션 시작
# ==========================================
class StartSessionRequest(BaseModel):
    classification_id: Optional[str] = None
    persona_type: Optional[str] = "empathy"


@router.post("/sessions")
async def start_session(
    body: StartSessionRequest,
    current_user: dict = Depends(get_current_user),
    db_sensitive: AsyncSession = Depends(get_db_sensitive),
    db_audit: AsyncSession = Depends(get_db_audit)
):
    """상담 세션 시작 → 기존 active 세션 자동 종료 후 새 세션 생성"""
    try:
        # 기존 active 세션 있으면 자동 종료 + 요약 저장
        existing = await db_sensitive.execute(
            select(CounselingSession).where(
                CounselingSession.user_id == uuid.UUID(current_user["user_id"]),
                CounselingSession.is_active == True,
                CounselingSession.deleted_at == None
            )
        )
        old_session = existing.scalar()
        if old_session:
            await close_session_with_summary(old_session, db_sensitive, db_audit)

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
CRISIS_THRESHOLD = 0.7

class SaveMessageRequest(BaseModel):
    role: str
    message_type: Optional[str] = "text"
    encrypted_content: str
    crisis_score: Optional[float] = None


@router.post("/sessions/{session_id}/messages")
async def save_message(
    session_id: str,
    body: SaveMessageRequest,
    current_user: dict = Depends(get_current_user),
    db_sensitive: AsyncSession = Depends(get_db_sensitive),
    db_audit: AsyncSession = Depends(get_db_audit)
):
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

        new_summary = await close_session_with_summary(session, db_sensitive, db_audit)

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