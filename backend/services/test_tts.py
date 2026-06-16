# test_tts.py

import asyncio

from tts_service import generate_voice_file


async def main():

    path = await generate_voice_file(
        text="안녕하세요. 하트비트 테스트입니다.",
        voice="ko-KR-HyunsuMultilingualNeural"
    )

    print(path)


asyncio.run(main())