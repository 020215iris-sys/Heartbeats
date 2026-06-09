import os
import re
import uuid
import json
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models import Conversation, CounselingSession, Summary
from core.security import verify_access_token
from core.crypto import encrypt_content
from routers.counseling import close_session_with_summary
from services.audit_service import log_sensitive

load_dotenv()

# ─────────────────────────────────────────
# Groq 클라이언트
# ─────────────────────────────────────────
groq_client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)

# ─────────────────────────────────────────
# 프롬프트 로드
# ─────────────────────────────────────────
AGENT_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "../../ai/prompts/active/prompt_agent_prompt.txt")
with open(AGENT_PROMPT_PATH, "r", encoding="utf-8") as f:
    AGENT_PROMPT = f.read()

GENERAL_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "../../ai/prompts/active/general_prompt.txt")
with open(GENERAL_PROMPT_PATH, "r", encoding="utf-8") as f:
    GENERAL_PROMPT = f.read()

# ─────────────────────────────────────────
# 세션별 system_prompt 캐시
# ─────────────────────────────────────────
SESSION_PROMPT_CACHE: dict[str, str] = {}


# ─────────────────────────────────────────
# 외국어 감지
# ─────────────────────────────────────────
def contains_foreign(text: str) -> bool:
    pattern = r"[^가-힣ᄀ-ᇿ㄰-㆏\s0-9.,!?~\-\'\"()…·]"  # 수정필요함 ★
    return bool(re.search(pattern, text))


# ─────────────────────────────────────────
# /chat 비즈니스 로직
# ─────────────────────────────────────────
async def process_chat(
    message: str,
    session_id: str,
    history: list[dict],
    token: str,
    db_sensitive: AsyncSession,
    db_audit: AsyncSession,
) -> str:

    # 1. JWT 토큰에서 user_id 꺼내기
    token = token.replace("Bearer ", "")
    current_user = verify_access_token(token)

    # 2. session_id로 counseling_session 조회 → 없으면 자동 생성
    result = await db_sensitive.execute(
        select(CounselingSession).where(
            CounselingSession.id == uuid.UUID(session_id),
            CounselingSession.deleted_at == None
        )
    )
    counseling_session = result.scalar()

    if not counseling_session:
        counseling_session = CounselingSession(
            id=uuid.UUID(session_id),
            user_id=uuid.UUID(current_user["user_id"]),
            persona_type="empathy",
            is_active=True
        )
        db_sensitive.add(counseling_session)
        await db_sensitive.flush()

    # 3. 60분 타임아웃 체크
    use_summary = False

    last_msg = await db_sensitive.execute(
        select(Conversation)
        .where(Conversation.session_id == uuid.UUID(session_id))
        .order_by(Conversation.created_at.desc())
        .limit(1)
    )
    last = last_msg.scalar()
    if last:
        elapsed = datetime.now(timezone.utc) - last.created_at.replace(tzinfo=timezone.utc)
        if elapsed > timedelta(minutes=60):
            await close_session_with_summary(counseling_session, db_sensitive, db_audit)
            SESSION_PROMPT_CACHE.pop(str(counseling_session.id), None)
            counseling_session.ended_at = datetime.now(timezone.utc)
            counseling_session.is_active = False
            await db_sensitive.flush()
            counseling_session = CounselingSession(
                user_id=uuid.UUID(current_user["user_id"]),
                persona_type="empathy",
                is_active=True
            )
            db_sensitive.add(counseling_session)
            await db_sensitive.flush()
            use_summary = True

    # 4. system_prompt 결정
    summary_result = await db_sensitive.execute(
        select(Summary)
        .where(Summary.user_id == uuid.UUID(current_user["user_id"]))
        .order_by(Summary.created_at.desc())
        .limit(1)
    )
    recent_summary = summary_result.scalar()

    cache_key = str(counseling_session.id)

    if cache_key in SESSION_PROMPT_CACHE:
        system_content = SESSION_PROMPT_CACHE[cache_key]

    elif recent_summary:
        # 재상담: Agent가 요약 기반으로 system_prompt 생성
        prompt_agent_input = {
            "nickname": current_user.get("nickname", "사용자"),
            "classification_results": {},
            "summary": {
                "main_complaint": recent_summary.main_complaint,
                "core_topics": recent_summary.core_topics,
                "next_session_notes": recent_summary.next_session_notes,
                "prompt_adjustment": recent_summary.prompt_adjustment,
            },
            "risk_level": recent_summary.risk_level,
            "suicidal_mentioned": recent_summary.suicidal_mentioned,
        }
        agent_response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": AGENT_PROMPT},
                {"role": "user", "content": json.dumps(prompt_agent_input, ensure_ascii=False)},
            ]
        )
        raw = agent_response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.strip("`").strip()
            if raw[:4].lower() == "json":
                raw = raw[4:].strip()
        agent_result = json.loads(raw)
        system_content = agent_result["system_prompt"]
        SESSION_PROMPT_CACHE[cache_key] = system_content

    else:
        # 첫 대화: general_prompt 사용
        system_content = GENERAL_PROMPT
        SESSION_PROMPT_CACHE[cache_key] = system_content

    # 5. Groq 응답 요청
    messages_to_send = (
        [{"role": "system", "content": system_content},
         {"role": "user", "content": message}]
        if use_summary else
        [{"role": "system", "content": system_content},
         *history,
         {"role": "user", "content": message}]
    )

    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages_to_send
    )
    reply = response.choices[0].message.content

    print("=== REPLY CHECK ===", reply)
    

    # 6. 외국어 감지 시 재요청
    if contains_foreign(reply):
        foreign_system = system_content + "\n\n반드시 한글로만 응답하세요. 영어나 다른 언어를 절대 사용하지 마세요."
        messages_foreign = (
            [{"role": "system", "content": foreign_system},
             {"role": "user", "content": message}]
            if use_summary else
            [{"role": "system", "content": foreign_system},
             *history,
             {"role": "user", "content": message}]
        )
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages_foreign
        )
        reply = response.choices[0].message.content
        if contains_foreign(reply):
            reply = "죄송해요. 그 부분에 대한 건 답변이 어려워요."

    # 7. 사용자/AI 메시지 저장
    ciphertext, key_id = encrypt_content(message)
    user_msg = Conversation(
        session_id=counseling_session.id,
        user_id=uuid.UUID(current_user["user_id"]),
        role="user",
        message_type="text",
        encrypted_content=ciphertext,
        encryption_key_id=key_id
    )
    db_sensitive.add(user_msg)

    ciphertext, key_id = encrypt_content(reply)
    ai_msg = Conversation(
        session_id=counseling_session.id,
        user_id=uuid.UUID(current_user["user_id"]),
        role="assistant",
        message_type="text",
        encrypted_content=ciphertext,
        encryption_key_id=key_id
    )
    db_sensitive.add(ai_msg)

    # 8. 감사 로그
    await log_sensitive(db_audit, current_user["user_id"], "CREATE", "CONVERSATION", user_msg.id)
    await log_sensitive(db_audit, current_user["user_id"], "CREATE", "CONVERSATION", ai_msg.id)

    await db_sensitive.commit()
    await db_audit.commit()

    return reply
