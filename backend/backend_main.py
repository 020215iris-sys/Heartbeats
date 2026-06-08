from contextlib import asynccontextmanager
from fastapi import FastAPI, Header, Depends
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from database import engine_general, engine_sensitive, engine_audit, get_db_sensitive, get_db_audit
from models import BaseGeneral, BaseSensitive, BaseAudit
from routers import auth, counseling
from sqlalchemy.ext.asyncio import AsyncSession

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
    from services.chat_service import process_chat
    reply = await process_chat(
        message=body.message,
        session_id=body.session_id,
        history=body.history,
        token=authorization,
        db_sensitive=db_sensitive,
        db_audit=db_audit,
    )
    return {"reply": reply}