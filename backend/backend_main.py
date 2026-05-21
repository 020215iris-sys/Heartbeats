from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()
import os

# 파일 분리 구조(방법 B)에 맞춰 우리가 새로 만든 파일들 불러오기
from routers import auth
from database import engine_general, engine_audit
from models import Base


# 앱 초기화 (타이틀 추가)
app = FastAPI(title="Heartbeats API")

# ==========================================
# 1. AI 채팅 (Groq) 설정 (기존 코드 유지)
# ==========================================
client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)

class Message(BaseModel):
    message: str

# ==========================================
# 2. 라우터 등록 (프론트 연결용 API)
# ==========================================
# 아까 만든 auth.py(회원가입/로그인)를 메인 앱에 붙여줍니다.
app.include_router(auth.router)

# ==========================================
# 3. 서버 시작 시 실행될 로직 (DB 테이블 생성)
# ==========================================
@app.on_event("startup")
async def startup():
    # 개발 초기 단계용: 앱 켜질 때 DB에 테이블 없으면 자동 생성
    async with engine_general.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with engine_audit.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# ==========================================
# 4. API 엔드포인트
# ==========================================
@app.get("/")
def root():
    return {"message": "Heartbeats API 서버 작동 중 (Auth 및 Chat 연결 완료)!"}

@app.post("/chat")
def chat(body: Message):
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "당신은 심리 상담사입니다."},
            {"role": "user", "content": body.message}
        ]
    )
    return {"reply": response.choices[0].message.content}