# services/persona_service.py

def build_persona_prompt(persona: dict) -> str:
    """
    persona: {"따듯함": 8, "공감도": 3, "직접성": 7, "말수": 4, "전문성": 6}
    → 프롬프트 문자열 반환
    """
    if not persona:
        return ""

    lines = [
        "[페르소나 설정]",
        "아래는 사용자가 설정한 상담 스타일 가중치입니다. 1~10 사이의 값이며 높을수록 해당 특성이 강합니다.",
        "이 값을 참고하여 말투와 응답 스타일을 조절하세요.",
        "",
    ]

    for key, value in persona.items():
        lines.append(f"- {key}: {value}/10")

    return "\n".join(lines)