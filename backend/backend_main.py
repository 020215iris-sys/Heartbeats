from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)

class Message(BaseModel):
    message: str

@app.get("/")
def root():
    return {"message": "Heartbeat API 서버 작동 중"}

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