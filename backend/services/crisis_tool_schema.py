"""
services/crisis_tool_schema.py

위기 감지용 Groq Function Calling Tool Schema.
chat_service.py의 기존 Groq 호출에 붙여서 사용.
llm_crisis_detector.py 대체.

사용법:
    from services.crisis_tool_schema import CRISIS_TOOL, CRISIS_TOOL_INSTRUCTION

    # system_content 뒤에 지시문 추가
    system_content += CRISIS_TOOL_INSTRUCTION

    # Groq 호출 시 tool 추가
    response = client.chat.completions.create(
        model=...,
        messages=messages,
        tools=[CRISIS_TOOL],
        tool_choice="auto"
    )

    # tool_calls 분기
    message = response.choices[0].message
    if message.tool_calls:
        args = json.loads(message.tool_calls[0].function.arguments)
        # 위기 처리
    else:
        reply = message.content
        # 일반 상담 응답
"""

CRISIS_TOOL = {
    "type": "function",
    "function": {
        "name": "report_crisis_assessment",
        "description": (
            "반드시 아래 상황에서만 호출하십시오. "
            "일반적인 우울감, 스트레스, 피곤함, 시험 걱정, 직장 고민은 호출 대상이 아닙니다. "
            "확실한 자살 사고, 자해 의도, 극단적 선택 암시, "
            "통제 불가능한 공황 상태일 때만 호출하십시오. "
            "위기 상황이 감지되면 상담 응답 생성보다 이 tool 호출을 우선하십시오."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "severity": {
                    "type": "string",
                    "enum": ["critical", "high", "medium"],
                    "description": (
                        "심각도. "
                        "critical: 자살/자해를 직접적으로 언급하거나 즉각적 위험 상태, "
                        "high: 강한 포기감, 사라지고 싶다는 표현, 삶에 대한 의지 상실, "
                        "medium: 통제 불가능한 공황, 극도의 불안, 죽을 것 같은 신체 증상"
                    )
                },
                "category": {
                    "type": "string",
                    "enum": ["suicide", "self_harm", "hopelessness", "panic"],
                    "description": (
                        "감지된 위기 카테고리. "
                        "suicide: 자살 사고 또는 계획 직접 표현, "
                        "self_harm: 자해 의도 또는 행위 표현, "
                        "hopelessness: 극단적 포기감, 사라지고 싶음, 삶의 의지 상실 (살기 싫다, 사라지고 싶다, 다 끝내고 싶다, 더 버티기 힘들다 등), "
                        "panic: 공황으로 의심되는 상태 (호흡 곤란, 극도의 공포, 심장 두근거림, 현실감 상실 등)"
                    )
                },
                "reason": {
                    "type": "string",
                    "description": "위기로 판단한 근거 한 줄 요약"
                }
            },
            "required": ["severity", "category", "reason"]
        }
    }
}

# 기존 system_content 뒤에 append해서 사용
# 기존 GENERAL_PROMPT / Agent 생성 프롬프트 구조를 건드리지 않음
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
