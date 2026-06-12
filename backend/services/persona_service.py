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




# ------chat_service.py
# system_content 완성 후, CRISIS_TOOL_INSTRUCTION 붙이기 전에 추가


# 4. system_prompt 결정 부분 끝에 추가
from services.persona_service import build_persona_prompt

# persona_type이 dict로 저장되어 있음
persona_data = counseling_session.persona_type  # {"따듯함": 8, ...}
if isinstance(persona_data, dict):
    persona_prompt = build_persona_prompt(persona_data)
    if persona_prompt:
        system_content += "\n\n" + persona_prompt

system_content += "\n\n" + CRISIS_TOOL_INSTRUCTION


# ------- 혹시나 날라갈까바

CRISIS_TOOL_INSTRUCTION = """
---
[위기 감지 지시]
반드시 사용자의 **현재 발화(마지막 메시지)만** 기준으로 판단하십시오.
이전 대화에 위험 표현이 있었더라도, 현재 발화가 위험하지 않으면 호출하지 마십시오.

호출 대상 (현재 발화 기준):
- 자살 의도 또는 계획을 현재 시점에서 직접 표현
- 자해 의도 또는 행위를 현재 시점에서 표현
- 극단적 선택을 현재 시점에서 암시 ("다 끝내고 싶다", "사라지고 싶다", "없어지고 싶다" 등)
- 통제 불가능한 공황 상태를 현재 시점에서 표현

호출 대상 아님:
- 이전 대화에서 언급된 위험 표현 (현재는 해소/부정된 경우)
- "아냐", "아니야", "그건 아니야" 등 부정·해명 발화
- "안 죽어", "괜찮아", "그냥 한 말이야" 등 이전 발언을 취소하는 표현
- 일반적인 우울감, 피곤함, 무기력감
- 시험/직장/관계 스트레스
- "힘들다", "지친다" 단독 표현
"""