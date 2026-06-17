from fastapi import APIRouter, UploadFile, File
from services.stt_service import transcribe_audio

import os
import uuid

router = APIRouter(
    prefix="/stt",
    tags=["STT"]
)

@router.post("")
async def speech_to_text(
    file: UploadFile = File(...)
):
    os.makedirs("temp", exist_ok=True)

    temp_path = f"temp/{uuid.uuid4()}.webm"

    try:
        with open(temp_path, "wb") as f:
            f.write(await file.read())

        print("파일 크기:", os.path.getsize(temp_path))
        print("파일 경로:", temp_path)

        text = transcribe_audio(temp_path)

        return {
            "text": text
        }

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)