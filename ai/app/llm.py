from groq import Groq
from dotenv import load_dotenv
import os

load_dotenv()

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

def generate_response(system_prompt, user_input):

    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_input,
            }
        ],
        model="llama-3.3-70b-versatile",
    )

    return chat_completion.choices[0].message.content

# -----------------------------------------------------------------------
# 위기 감지 포함 응답 생성 (기존 generate_response를 이걸로 대체)
# -----------------------------------------------------------------------
from backend.services.crisis_detector import detect_crisis
from backend.services.crisis_response import get_crisis_response_message

def generate_response_with_crisis_check(system_prompt: str, user_input: str):
    """
    반환값:
        {
            "response": str,          # 상담 응답 or 안내 문구
            "is_crisis": bool,
            "crisis_result": CrisisDetectionResult or None
        }
    """
    result = detect_crisis(user_input)

    if result.detected:
        return {
            "response": get_crisis_response_message(result.severity),
            "is_crisis": True,
            "crisis_result": result,
        }

    # 위험 없음 → 기존 상담 LLM 호출
    return {
        "response": generate_response(system_prompt, user_input),
        "is_crisis": False,
        "crisis_result": None,
    }