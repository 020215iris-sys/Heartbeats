import uuid
from pathlib import Path

import edge_tts

VOICE_DIR = Path("voice")
VOICE_DIR.mkdir(exist_ok=True)


async def generate_voice_file(
    text: str,
    voice: str,
) -> str:
    filename = f"{uuid.uuid4()}.mp3"

    filepath = VOICE_DIR / filename

    communicate = edge_tts.Communicate(
        text=text,
        voice=voice
    )

    await communicate.save(str(filepath))

    return str(filepath)