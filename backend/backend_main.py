from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, Depends
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()
import os
import re
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database import engine_general, engine_sensitive, engine_audit, get_db_sensitive, get_db_audit
from models import BaseGeneral, BaseSensitive, BaseAudit, Conversation, AuditLogSensitive, CounselingSession, Summary  # ← 14번줄: Summary 추가
from routers import auth, counseling
from core.security import verify_access_token
from core.crypto import encrypt_content
from datetime import datetime, timezone, timedelta
import json

SESSION_PROMPT_CACHE: dict[str, str] = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine_general.begin() as conn:
        await conn.run_sync(BaseGeneral.metadata.create_all, checkfirst=True)
    async with engine_sensitive.begin() as conn:
        await conn.run_sync(BaseSensitive.metadata.create_all, checkfirst=True)
    async with engine_audit.begin() as conn:
        await conn.run_sync(BaseAudit.metadata.create_all, checkfirst=True)
    yield

app = FastAPI(title="Heartbeats API", lifespan=lifespan)

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)

AGENT_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "../ai/prompts/active/prompt_agent_prompt.txt")
with open(AGENT_PROMPT_PATH, "r", encoding="utf-8") as f:
    AGENT_PROMPT = f.read()

def contains_foreign(text: str) -> bool:
    # 한글, 공백, 숫자, 문장부호만 허용
    pattern = r"[^\uAC00-\uD7A3\u1100-\u11FF\u3130-\u318F\s0-9.,!?~\-\'\"()…·]"
    return bool(re.search(pattern, text))

class Message(BaseModel):
    message: str
    session_id: str
    history: list[dict] = []

app.include_router(auth.router)
app.include_router(counseling.router)

@app.get("/")
def root():
    return {"message": "Heartbeats API 서버 작동 중 (Auth 및 Chat 연결 완료)!"}

@app.post("/chat")
async def chat(
    body: Message,
    authorization: str = Header(...),
    db_sensitive: AsyncSession = Depends(get_db_sensitive),
    db_audit: AsyncSession = Depends(get_db_audit)
):
    # 1. JWT 토큰에서 user_id 꺼내기
    token = authorization.replace("Bearer ", "")
    current_user = verify_access_token(token)

    # 2. session_id로 counseling_sessions 조회 → 없으면 자동 생성
    result = await db_sensitive.execute(
        select(CounselingSession).where(
            CounselingSession.id == uuid.UUID(body.session_id),
            CounselingSession.deleted_at == None
        )
    )
    counseling_session = result.scalar()

    if not counseling_session:
        counseling_session = CounselingSession(
            id=uuid.UUID(body.session_id),
            user_id=uuid.UUID(current_user["user_id"]),
            persona_type="empathy",
            is_active=True
        )
        db_sensitive.add(counseling_session)
        await db_sensitive.flush()

    # 2-1. 마지막 메시지 시간 체크 (60분 타이머)s

    use_summary = False  #  요약 기반 여부 플래그

    last_msg = await db_sensitive.execute(
        select(Conversation)
        .where(Conversation.session_id == uuid.UUID(body.session_id))
        .order_by(Conversation.created_at.desc())
        .limit(1)
    )
    last = last_msg.scalar()
    if last:
        elapsed = datetime.now(timezone.utc) - last.created_at.replace(tzinfo=timezone.utc)
        if elapsed > timedelta(minutes=60):
            from routers.counseling import close_session_with_summary
            await close_session_with_summary(counseling_session, db_sensitive, db_audit)
            SESSION_PROMPT_CACHE.pop(str(counseling_session.id), None)
            # session_expired 반환 대신 조용히 세션 종료 + 새 세션 생성
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
            use_summary = True  # 이제 요약 기반으로 대화

    # 2-2. 요약 기반이면 DB에서 최근 요약 조회 
    summary_result = await db_sensitive.execute(
        select(Summary)
        .where(Summary.user_id == uuid.UUID(current_user["user_id"]))
        .order_by(Summary.created_at.desc())
        .limit(1)
    )
    
    recent_summary = summary_result.scalar()

    # 테스트용 
    # prompt_agent_input = {
    #     "nickname": "사용자",
    #     "classification_results": {},

    #     "summary": {
    #         "main_complaint": "부모와의 갈등으로 인한 스트레스",
    #         "core_topics": [
    #             "부모갈등",
    #             "가족관계",
    #             "스트레스"
    #         ],
    #         "next_session_notes": "부모와 대화 시도 결과 확인 필요",
    #         "prompt_adjustment": [
    #             "emotional_support",
    #             "reflection",
    #             "family_relationship"
    #         ],
    #     },

    #     "important_memory": [
    #         "사용자는 형과 지속적으로 비교당한다고 느낌",
    #         "부모와 솔직하게 대화해보기로 약속함",
    #         "취업 면접 결과를 기다리고 있음"
    #     ],

    #     "risk_level": "medium",
    #     "suicidal_mentioned": False,
    # }

    # print("=== PROMPT AGENT INPUT ===")
    # print(prompt_agent_input)

    cache_key = str(counseling_session.id)

    if cache_key in SESSION_PROMPT_CACHE:
        system_content = SESSION_PROMPT_CACHE[cache_key]

    elif recent_summary:
        prompt_agent_input = {
            "nickname": current_user.get("nickname", "사용자"),
            "classification_results": {},
            "summary": {
                "main_complaint": recent_summary.main_complaint,
                "core_topics": recent_summary.core_topics,
                "next_session_notes": recent_summary.next_session_notes,
                "prompt_adjustment": recent_summary.prompt_adjustment,
            }, "important_memory": recent_summary.important_memory or [],
            "risk_level": recent_summary.risk_level,
            "suicidal_mentioned": recent_summary.suicidal_mentioned,
        }
        agent_response = client.chat.completions.create(
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
        system_content = ""


    # 3. Groq한테 응답 요청
    # use_summary 여부에 따라 history vs 요약 선택
    messages_to_send = (
        [{"role": "system", "content": system_content},
         {"role": "user", "content": body.message}]
        if use_summary else
        [{"role": "system", "content": system_content},
         *body.history,
         {"role": "user", "content": body.message}]
    )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages_to_send  # messages_to_send 사용
    )
    reply = response.choices[0].message.content


    print("=== REPLY CHECK ===", reply)
    # 외국어 감지 시 재요청

    if contains_foreign(reply):
        foreign_system = system_content + "\n\n반드시 한글로만 응답하세요. 영어나 다른 언어를 절대 사용하지 마세요."
        messages_foreign = (
            [{"role": "system", "content": foreign_system},
             {"role": "user", "content": body.message}]
            if use_summary else
            [{"role": "system", "content": foreign_system},
             *body.history,
             {"role": "user", "content": body.message}]
        )
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages_foreign
        )
        reply = response.choices[0].message.content
        if contains_foreign(reply):
            reply = "죄송해요. 그 부분에 대한 건 답변이 어려워요."

    # 4. 사용자 메시지 저장
    ciphertext, key_id = encrypt_content(body.message)
    user_msg = Conversation(
        session_id=counseling_session.id,  # 새 세션 id 사용
        user_id=uuid.UUID(current_user["user_id"]),
        role="user",
        message_type="text",
        encrypted_content=ciphertext,
        encryption_key_id=key_id
    )
    db_sensitive.add(user_msg)

    # 5. AI 응답 저장
    ciphertext, key_id = encrypt_content(reply)
    ai_msg = Conversation(
        session_id=counseling_session.id,  # 새 세션 id 사용
        user_id=uuid.UUID(current_user["user_id"]),
        role="assistant",
        message_type="text",
        encrypted_content=ciphertext,
        encryption_key_id=key_id
    )

    db_sensitive.add(ai_msg)

    # 6. 감사 로그
    audit_log_user = AuditLogSensitive(
        user_id=uuid.UUID(current_user["user_id"]),
        action="CREATE",
        resource_type="CONVERSATION",
        resource_id=user_msg.id
    )
    audit_log_ai = AuditLogSensitive(
        user_id=uuid.UUID(current_user["user_id"]),
        action="CREATE",
        resource_type="CONVERSATION",
        resource_id=ai_msg.id
    )
    db_audit.add(audit_log_user)
    db_audit.add(audit_log_ai)

    await db_sensitive.commit()
    await db_audit.commit()

    return {"reply": reply}