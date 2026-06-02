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
from routers.auth import verify_access_token
from core.crypto import encrypt_content
from datetime import datetime, timezone, timedelta

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

PROMPT_PATH = os.path.join(os.path.dirname(__file__), "../ai/prompts/active/general_prompt.txt")
with open(PROMPT_PATH, "r", encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read()

def contains_foreign(text: str) -> bool:
    pattern = r"[一-龯ぁ-ゔァ-ヴー々〆〤a-zA-Z]"
    return re.search(pattern, text) is not None

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
    system_content = SYSTEM_PROMPT
    if use_summary:
        summary_result = await db_sensitive.execute(
            select(Summary)
            .where(Summary.user_id == uuid.UUID(current_user["user_id"]))
            .order_by(Summary.created_at.desc())
            .limit(1)
        )
        recent_summary = summary_result.scalar()
        if recent_summary:
            system_content = SYSTEM_PROMPT + (
                f"\n\n[이전 상담 요약]"
                f"\n주요 호소: {recent_summary.main_complaint}"
                f"\n핵심 주제: {recent_summary.core_topics}"
                f"\n다음 상담 이어갈 내용: {recent_summary.next_session_notes}"
            )

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
        model="llama-3.1-70b-versatile",
        messages=messages_to_send  # messages_to_send 사용
    )
    reply = response.choices[0].message.content

    # 외국어 감지 시 재요청
    if contains_foreign(reply):
        foreign_system = system_content + "\n\n반드시 한국어로만 응답하세요. 영어나 다른 언어를 절대 사용하지 마세요."
        messages_foreign = (
            [{"role": "system", "content": foreign_system},
             {"role": "user", "content": body.message}]
            if use_summary else
            [{"role": "system", "content": foreign_system},
             *body.history,
             {"role": "user", "content": body.message}]
        )
        response = client.chat.completions.create(
            model="llama-3.1-70b-versatile",
            messages=messages_foreign 
        )
        reply = response.choices[0].message.content

    # 4. 사용자 메시지 저장
    ciphertext, key_id = encrypt_content(body.message)
    user_msg = Conversation(
        session_id=counseling_session.id,  # 새 세션 id 사용
        user_id=uuid.UUID(current_user["user_id"]),
        role="user",
        message_type="text",
        encrypted_content=ciphertext,
        encryption_key_id="none"
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
        encryption_key_id="none"
    )
    db_sensitive.add(ai_msg)

    # 6. 감사 로그
    audit_log = AuditLogSensitive(
        user_id=uuid.UUID(current_user["user_id"]),
        action="CREATE",
        resource_type="CONVERSATION",
        resource_id=user_msg.id
    )
    db_audit.add(audit_log)

    await db_sensitive.commit()
    await db_audit.commit()

    return {"reply": reply}