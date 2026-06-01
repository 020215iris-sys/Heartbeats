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
from models import BaseGeneral, BaseSensitive, BaseAudit, Conversation, AuditLogSensitive, CounselingSession
from routers import auth, counseling
from routers.auth import verify_access_token


# ==========================================
# 서버 시작/종료 시 실행될 로직
# checkfirst=True → 테이블 이미 있으면 스킵
# ==========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine_general.begin() as conn:
        await conn.run_sync(BaseGeneral.metadata.create_all, checkfirst=True)
    async with engine_sensitive.begin() as conn:
        await conn.run_sync(BaseSensitive.metadata.create_all, checkfirst=True)
    async with engine_audit.begin() as conn:
        await conn.run_sync(BaseAudit.metadata.create_all, checkfirst=True)
    yield


# 앱 초기화
app = FastAPI(title="Heartbeats API", lifespan=lifespan)

# ==========================================
# AI 채팅 (Groq) 설정
# ==========================================
client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)

# ==========================================
# 프롬프트 파일 로드
# ==========================================
PROMPT_PATH = os.path.join(os.path.dirname(__file__), "../ai/prompts/active/general_prompt.txt")
with open(PROMPT_PATH, "r", encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read()

# ==========================================
# 외국어 감지 함수 (ai/archive/validator.py)
# ==========================================
def contains_foreign(text: str) -> bool:
    pattern = r"[一-龯ぁ-ゔァ-ヴー々〆〤a-zA-Z]"
    return re.search(pattern, text) is not None

# ==========================================
# /chat 요청 모델
# ==========================================
class Message(BaseModel):
    message: str
    session_id: str
    history: list[dict] = []  # [{"role": "user"/"assistant", "content": "..."}]

# ==========================================
# 라우터 등록
# ==========================================
app.include_router(auth.router)
app.include_router(counseling.router)

# ==========================================
# API 엔드포인트
# ==========================================
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

    # 3. Groq한테 응답 요청 (이전 대화 history 포함)
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            *body.history,
            {"role": "user", "content": body.message}
        ]
    )
    reply = response.choices[0].message.content

    # 외국어 감지 시 재요청
    if contains_foreign(reply):
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT + "\n\n반드시 한국어로만 응답하세요. 영어나 다른 언어를 절대 사용하지 마세요."},
                *body.history,
                {"role": "user", "content": body.message}
            ]
        )
        reply = response.choices[0].message.content

    # 4. 사용자 메시지 저장
    user_msg = Conversation(
        session_id=uuid.UUID(body.session_id),
        user_id=uuid.UUID(current_user["user_id"]),
        role="user",
        message_type="text",
        encrypted_content=body.message,
        encryption_key_id="none"
    )
    db_sensitive.add(user_msg)

    # 5. AI 응답 저장
    ai_msg = Conversation(
        session_id=uuid.UUID(body.session_id),
        user_id=uuid.UUID(current_user["user_id"]),
        role="assistant",
        message_type="text",
        encrypted_content=reply,
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