"""
상담사 페르소나 정의.

ERD의 COUNSELING_SESSIONS.persona_type ("empathy/coaching/neutral") 와 동기.
백엔드가 페르소나 코드로 LLM 프롬프트 전략을 분기할 때 같은 식별자 공유.

확장 시:
    - 새 페르소나 추가는 PERSONAS dict에 항목만 추가
    - 사용자 페르소나 선택 기능 만들 때는 session["persona_code"] 사용
    - 추후 일러스트 이미지가 생기면 avatar_image 필드 추가
"""

# 페르소나 데이터.
# avatar_emoji는 MVP용 임시. 추후 SVG/이미지로 교체.
PERSONAS = {
    "empathy": {
        "code": "empathy",
        "name": "다온",
        "tagline": "공감과 경청 중심",
        "greeting": "안녕하세요. 오늘은 어떤 이야기를 들려주실래요?",
        "avatar_emoji": "🌱",
        "accent_color": "brand",   # Tailwind 클래스 prefix
    },
    "coaching": {
        "code": "coaching",
        "name": "라온",
        "tagline": "실행 중심 코칭",
        "greeting": "반가워요. 무엇을 함께 정리해볼까요?",
        "avatar_emoji": "✨",
        "accent_color": "amber",
    },
    "neutral": {
        "code": "neutral",
        "name": "온유",
        "tagline": "중립적 안내",
        "greeting": "환영합니다. 편하게 말씀해주세요.",
        "avatar_emoji": "💧",
        "accent_color": "slate",
    },
}

DEFAULT_PERSONA_CODE = "empathy"


def get_persona(code: str | None = None) -> dict:
    """
    페르소나 dict 반환. code가 None이거나 없는 코드면 기본값.
    """
    if not code or code not in PERSONAS:
        code = DEFAULT_PERSONA_CODE
    return PERSONAS[code]