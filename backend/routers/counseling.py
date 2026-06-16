from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
from database import get_db_sensitive, get_db_audit
from models import CounselingSession, Conversation, CrisisEvent, AuditLogSensitive, Summary
from sqlalchemy.future import select
from sqlalchemy import func
from datetime import datetime, timezone
from core.security import get_current_user
from openai import OpenAI, RateLimitError
import uuid
import json
import os
import yaml
from core.crypto import decrypt_content, encrypt_content, encrypt_json
from services.summary_service import request_summary
from services.personas import normalize_persona, DEFAULT_PERSONA


router = APIRouter(prefix="/counseling", tags=["Counseling"])

class ChatMessage(BaseModel):
    message: str
    session_id: str
    history: list[dict] = []
    persona: Optional[dict] = None

@router.post("/chat")
async def chat(
    body: ChatMessage,
    authorization: str = Header(...),
    db_sensitive: AsyncSession = Depends(get_db_sensitive),
    db_audit: AsyncSession = Depends(get_db_audit),
):
    from services.chat_service import process_chat
    try:
        reply = await process_chat(
            message=body.message,
            session_id=body.session_id,
            history=body.history,
            persona=body.persona,
            token=authorization,
            db_sensitive=db_sensitive,
            db_audit=db_audit,
        )
    except RateLimitError:
        # LLM(Cerebras) 접속량 초과(429) → 500이 아니라 429로 명시해서 내려줌.
        # 프론트는 429일 때 "접속량이 많습니다" 안내 문구를 노출한다.
        await db_sensitive.rollback()
        await db_audit.rollback()
        raise HTTPException(
            status_code=429,
            detail="접속량이 많습니다. 잠시 후에 시도해주세요.",
        )
    return {"reply": reply}

groq_client = OpenAI(
    api_key=os.getenv("CEREBRAS_API_KEY"),
    base_url="https://api.cerebras.ai/v1",
)
# groq_client = OpenAI(
#     api_key=os.getenv("GROQ_API_KEY"),
#     base_url="https://api.groq.com/openai/v1",
# )
# ==========================================
# 세션 종료 + 요약 저장 공통 함수
# ==========================================
async def close_session_with_summary(session, db_sensitive, db_audit):
    """
    세션 종료 + 요약 저장 공통 함수.

    요약 API / Groq / YAML 파싱 중 하나가 실패해도
    summaries 저장 자체는 실패하지 않도록 방어한다.
    """
    session.ended_at = datetime.now(timezone.utc)
    session.is_active = False

    summary_data = {
        "main_complaint": "",
        "risk_level": "low",
        "suicidal_mentioned": False,
        "core_topics": [],
        "next_session_notes": "",
        "prompt_adjustment": [],
        "important_memory": [],
    }

    def strip_code_block(text_value: str) -> str:
        text_value = (text_value or "").strip()
        if text_value.startswith("```"):
            text_value = text_value.strip("`").strip()
            if text_value[:4].lower() == "json":
                text_value = text_value[4:].strip()
            elif text_value[:4].lower() == "yaml":
                text_value = text_value[4:].strip()
        return text_value

    def normalize_list(value):
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            items = []
            for line in value.splitlines():
                line = line.strip()
                if not line:
                    continue
                if line.startswith("-"):
                    line = line[1:].strip()
                items.append(line)
            return items
        return []

    def normalize_summary_data(data) -> dict:
        normalized = {
            "main_complaint": "",
            "risk_level": "low",
            "suicidal_mentioned": False,
            "core_topics": [],
            "next_session_notes": "",
            "prompt_adjustment": [],
            "important_memory": [],
        }

        if not isinstance(data, dict):
            return normalized

        normalized["main_complaint"] = data.get("main_complaint") or ""
        normalized["risk_level"] = data.get("risk_level") or "low"
        normalized["suicidal_mentioned"] = bool(data.get("suicidal_mentioned", False))
        normalized["core_topics"] = normalize_list(data.get("core_topics"))
        normalized["next_session_notes"] = data.get("next_session_notes") or ""
        normalized["important_memory"] = normalize_list(data.get("important_memory"))

        prompt_adjustment = data.get("prompt_adjustment")
        if isinstance(prompt_adjustment, dict):
            normalized["prompt_adjustment"] = prompt_adjustment
        else:
            normalized["prompt_adjustment"] = normalize_list(prompt_adjustment)

        return normalized

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

    raw_output = None

    try:
        summary_result = request_summary(transcript)

        print("=== SUMMARY RESULT RAW ===")
        print(json.dumps(summary_result, ensure_ascii=False, indent=2))

        if isinstance(summary_result, dict):

            if summary_result.get("success") is True:

                raw_output = summary_result.get("output", {})

            else:

                print("=== SUMMARY FALLBACK USED ===")
                print(summary_result.get("error"))

                raw_output = summary_result.get("output", {})

        else:
            raw_output = {}

        print("=== SUMMARY ===")
        print(raw_output)

    except Exception as e:
        print("=== SUMMARY API FAILED ===")
        print(str(e))

# ===== After =====
    if raw_output is not None:
        parsed_summary = None
        cleaned_output = ""

        # 0) 서버가 이미 dict로 파싱해서 준 경우 그대로 사용
        if isinstance(raw_output, dict):
            parsed_summary = raw_output
        else:
            cleaned_output = strip_code_block(raw_output)

            # 1) JSON 우선: 첫 '{' ~ 마지막 '}' 구간만 추출
            start = cleaned_output.find("{")
            end = cleaned_output.rfind("}")
            if start != -1 and end > start:
                try:
                    parsed_summary = json.loads(cleaned_output[start:end + 1])
                except Exception as e:
                    print("=== SUMMARY JSON PARSE FAILED ===")
                    print(str(e))

            # 2) JSON 실패 시 YAML
            if not isinstance(parsed_summary, dict):
                try:
                    parsed_summary = yaml.safe_load(cleaned_output)
                except Exception as e:
                    print("=== SUMMARY YAML PARSE FAILED ===")
                    print(str(e))
                    parsed_summary = None

        # 3) 둘 다 실패/비정상 → 기존 라인 파서 (마지막 안전망)
        if isinstance(parsed_summary, dict):
            summary_data = normalize_summary_data(parsed_summary)
        else:
            parsed_fallback = {}
            current_key = None
            items = []

            for line in cleaned_output.splitlines():
                line = line.strip()
                if not line:
                    continue

                if line.endswith(":") and not line.startswith("-"):
                    if current_key and items:
                        parsed_fallback[current_key] = items
                    current_key = line[:-1]
                    items = []
                elif line.startswith("-") and current_key:
                    items.append(line[1:].strip())
                elif current_key:
                    parsed_fallback[current_key] = line
                    current_key = None

            if current_key and items:
                parsed_fallback[current_key] = items

            summary_data = normalize_summary_data(parsed_fallback)


    try:
        risk_prompt = f"""
당신은 정신건강 상담 요약을 검토하는 분류기입니다.

아래 상담 요약을 읽고 다음 두 항목만 JSON으로 출력하세요.

1. risk_level: low | medium | high
2. suicidal_mentioned: true | false

판단 규칙:
- 자살, 자해, 죽고 싶음, 사라지고 싶음, 삶을 끝내고 싶음 등 표현이 있으면 suicidal_mentioned=true
- suicidal_mentioned=true이면 risk_level=high
- 반드시 JSON만 출력
- 설명은 출력하지 마세요

상담 요약:
main_complaint: {summary_data.get("main_complaint", "")}
core_topics: {summary_data.get("core_topics", [])}
next_session_notes: {summary_data.get("next_session_notes", "")}
prompt_adjustment: {summary_data.get("prompt_adjustment", [])}
"""

        risk_response = groq_client.chat.completions.create(
            model="gpt-oss-120b",
            messages=[
                {"role": "user", "content": risk_prompt}
            ]
        )

        risk_text = strip_code_block(risk_response.choices[0].message.content)
        if risk_text:
            risk_parsed = json.loads(risk_text)
            summary_data["risk_level"] = risk_parsed.get("risk_level", "low")
            summary_data["suicidal_mentioned"] = bool(
                risk_parsed.get("suicidal_mentioned", False)
            )

    except Exception as e:
        print("=== RISK CLASSIFICATION FAILED ===")
        print(str(e))

    # 최종 안전 장치
    summary_data.setdefault("main_complaint", "")
    summary_data.setdefault("risk_level", "low")
    summary_data.setdefault("suicidal_mentioned", False)
    summary_data.setdefault("core_topics", [])
    summary_data.setdefault("next_session_notes", "")
    summary_data.setdefault("prompt_adjustment", [])
    summary_data.setdefault("important_memory", [])
# W2 암호화: 평문을 BYTEA + key_id 짝으로 저장
    mc_bytes, mc_kid = encrypt_content(summary_data.get("main_complaint", "") or "")
    nsn_bytes, nsn_kid = encrypt_content(summary_data.get("next_session_notes", "") or "")

    # W3: core_topics, important_memory 듀얼 라이트
    ct_value = summary_data.get("core_topics", [])
    im_value = summary_data.get("important_memory", [])
    ct_bytes, ct_kid = encrypt_json(ct_value)
    im_bytes, im_kid = encrypt_json(im_value)

    new_summary = Summary(
        session_id=session.id,
        user_id=session.user_id,
        main_complaint_encrypted=mc_bytes,
        main_complaint_key_id=mc_kid,
        next_session_notes_encrypted=nsn_bytes,
        next_session_notes_key_id=nsn_kid,
        risk_level=summary_data.get("risk_level", "low"),
        suicidal_mentioned=summary_data.get("suicidal_mentioned", False),
        prompt_adjustment=summary_data.get("prompt_adjustment", []),    # 평문 유지
        # 옛 평문 (컷오버 전까지 듀얼 라이트)
        core_topics=ct_value,
        important_memory=im_value,
        # W3 암호화
        core_topics_encrypted=ct_bytes,
        core_topics_key_id=ct_kid,
        important_memory_encrypted=im_bytes,
        important_memory_key_id=im_kid,
    )

    db_sensitive.add(new_summary)
    await db_sensitive.flush()

    return new_summary

# ==========================================
# 내 세션 목록 조회
# ==========================================

@router.get("/sessions")
async def get_my_sessions(
    current_user: dict = Depends(get_current_user),
    db_sensitive: AsyncSession = Depends(get_db_sensitive),
    limit: Optional[int] = Query(default=None, ge=1, le=100),
):
    user_id = uuid.UUID(current_user["user_id"])

    stmt = (
        select(CounselingSession)
        .where(
            CounselingSession.user_id == user_id,
            CounselingSession.deleted_at == None
        )
        .order_by(CounselingSession.started_at.desc())
    )
    if limit:
        stmt = stmt.limit(limit)

    result = await db_sensitive.execute(stmt)
    sessions = result.scalars().all()

    session_ids = [s.id for s in sessions]

    # 세션별 message_count
    count_result = await db_sensitive.execute(
        select(Conversation.session_id, func.count(Conversation.id).label("cnt"))
        .where(
            Conversation.session_id.in_(session_ids),
            Conversation.deleted_at == None
        )
        .group_by(Conversation.session_id)
    )
    count_map = {row.session_id: row.cnt for row in count_result}

    # 세션별 summary → preview
    summary_result = await db_sensitive.execute(
        select(Summary)
        .where(
            Summary.user_id == user_id,
            Summary.deleted_at.is_(None),
        )
        .order_by(Summary.created_at.desc())
    )
    summaries = summary_result.scalars().all()
    summary_map = {}
    for s in summaries:
        if s.session_id and s.session_id not in summary_map:
            try:
                if s.main_complaint_encrypted is not None:
                    text = decrypt_content(
                        s.main_complaint_encrypted,
                        s.main_complaint_key_id,
                    )
                    if text:
                        summary_map[s.session_id] = text
            except Exception:
                pass  # map에 추가 안 함 → fallback으로 넘어감

    # 요약 없는 세션 → 첫 사용자 메시지 50자로 대체
    sessions_needing_fallback = [s.id for s in sessions if s.id not in summary_map]
    fallback_map = {}
    if sessions_needing_fallback:
        fallback_result = await db_sensitive.execute(
            select(Conversation)
            .where(
                Conversation.session_id.in_(sessions_needing_fallback),
                Conversation.role == "user",
                Conversation.deleted_at == None
            )
            .order_by(Conversation.created_at.asc())
        )
        for msg in fallback_result.scalars().all():
            if msg.session_id not in fallback_map:
                try:
                    text = decrypt_content(msg.encrypted_content, msg.encryption_key_id)
                    fallback_map[msg.session_id] = text[:50]
                except Exception:
                    fallback_map[msg.session_id] = ""

    return {
        "sessions": [
            {
                "session_id": str(s.id),
                "started_at": s.started_at.isoformat(),
                "persona_type": s.persona_type,
                "preview": summary_map.get(s.id) or fallback_map.get(s.id, ""),
                "message_count": count_map.get(s.id, 0),
            }
            for s in sessions
        ]
    }
# ==========================================
# 상담 세션 시작
# ==========================================
class StartSessionRequest(BaseModel):
    classification_id: Optional[str] = None
    persona_type: Optional[dict] = None  # 변경: str → dict (또는 None 시 서버 디폴트)


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

        # ↓↓↓ ★ 여기 (new_session 생성 직전) ★ ↓↓↓
        # ───────── 페르소나 정규화 + 스냅샷 페이로드 빌드 ─────────

        persona_payload = normalize_persona(body.persona_type)

        # ───────── 페르소나 정규화 끝 ─────────

        new_session = CounselingSession(
            user_id=uuid.UUID(current_user["user_id"]),
            classification_id=uuid.UUID(body.classification_id) if body.classification_id else None,
            persona_type=persona_payload, # 변경: body.persona_type → persona_payload
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

        ciphertext, key_id = encrypt_content(body.encrypted_content)
        new_message = Conversation(
            session_id=uuid.UUID(session_id),
            user_id=uuid.UUID(current_user["user_id"]),
            role=body.role,
            message_type=body.message_type,
            encrypted_content=ciphertext,
            encryption_key_id=key_id,
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
                "content": decrypt_content(m.encrypted_content, m.encryption_key_id),
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
