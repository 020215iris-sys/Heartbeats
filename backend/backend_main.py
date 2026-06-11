from contextlib import asynccontextmanager
from fastapi import FastAPI
from dotenv import load_dotenv

load_dotenv()

from database import engine_general, engine_sensitive, engine_audit
from models import BaseGeneral, BaseSensitive, BaseAudit
from routers import auth, counseling, survey, guardian


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

app.include_router(auth.router)
app.include_router(counseling.router)
app.include_router(survey.router)
app.include_router(guardian.router)

@app.get("/")
def root():
    return {"message": "Heartbeats API 서버 작동 중"}
