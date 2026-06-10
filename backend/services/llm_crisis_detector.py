"""
services/llm_crisis_detector.py

Groq Tool Use(Function Calling) 기반 위기 감지 모듈.
기존 keyword 방식(crisis_detector.py)의 LLM 버전.
"""

import json
import os
from openai import OpenAI
from services.crisis_detector import CrisisDetectionResult


client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)

# 카테고리 → severity 매핑
CATEGORY_SEVERITY_MAP = {
    "self_harm":     "critical",
    "direct_high":   "critical",
    "direct_medium": "high",
    "indirect":      "medium",
    "panic":         "medium",
}

# Groq에 넘길 tool 정의
CRISIS_TOOL = {
    "type": "function",
    "function": {
        "name": "report_crisis_assessment",
        "description": (
            "사용자의 발화를 분석해 위기 여부와 심각도를 보고합니다. "
            "위기 징후가 없으면 is_crisis=false, severity=none으로 보고합니다."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "is_crisis": {
                    "type": "boolean",
                    "description": "위기 징후 존재 여부"
                },
                "severity": {
                    "type": "string",
                    "enum": ["critical", "high", "medium", "low", "none"],
                    "description": (
                        "심각도. "
                        "critical: 자해/자살 직접 표현, "
                        "high: 강한 포기/사라짐 표현, "
                        "medium: 간접적 고통/공황 표현, "
                        "low: 경미한 부정적 감정, "
                        "none: 위기 없음"
                    )
                },
                "crisis_score": {
                    "type": "number",
                    "description": "위기 강도 점수 (0.0 ~ 1.0)"
                },
                "matched_category": {
                    "type": "string",
                    "enum": ["self_harm", "direct_high", "direct_medium", "indirect", "panic", "none"],
                    "description": "감지된 위기 카테고리. 위기 없으면 none"
                },
                "reason": {
                    "type": "string",
                    "description": "판단 근거 한 줄 요약 (한국어)"
                }
            },
            "required": ["is_crisis", "severity", "crisis_score", "matched_category", "reason"]
        }
    }
}

SYSTEM_PROMPT = """당신은 심리 상담 보조 시스템의 위기 감지 모듈입니다.
사용자의 발화 하나를 받아 위기 징후가 있는지 분석하고, 반드시 report_crisis_assessment 툴을 호출해 결과를 보고해야 합니다.

판단 기준:
- critical: 자살, 자해를 직접적으로 언급하거나 의도를 명확히 표현
- high: 강한 포기감, 사라지고 싶다는 표현
- medium: 간접적인 고통, 공황 증상, 삶의 무기력 표현
- low: 일시적인 부정적 감정 표현
- none: 위기 징후 없음

주의: 문맥 없이 발화 하나만 보고 판단합니다. 과도하게 민감하게 판단하지 마세요.
"""


def detect_crisis_llm(message: str) -> dict:
    """
    Groq Function Calling으로 위기 감지 실행.

    Args:
        message: 사용자 발화 (단일 턴)

    Returns:
        {
            "is_crisis": bool,
            "severity": str,       # critical / high / medium / low / none
            "crisis_score": float,
            "matched_category": str,
            "reason": str,
            "source": "llm"        # keyword 방식과 구분용
        }
    """
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": message}
            ],
            tools=[CRISIS_TOOL],
            tool_choice={"type": "function", "function": {"name": "report_crisis_assessment"}},
            temperature=0.0,   # 위기 감지는 결정론적으로
            max_tokens=256,
        )

        # tool_calls에서 인자 파싱
        tool_call = response.choices[0].message.tool_calls[0]
        args = json.loads(tool_call.function.arguments)

        return CrisisDetectionResult(
            detected=args.get("is_crisis", False),
            severity=args.get("severity", "none"),
            crisis_score=float(args.get("crisis_score", 0.0)),
            matched_keyword=args.get("matched_category", "none"),  # matched_keyword 필드에 category 담기
            category=args.get("matched_category", "none"),
        )

    except Exception as e:
        # 감지 실패 시 안전하게 none 반환 (서비스 중단 방지)
        return CrisisDetectionResult(
            detected=False,
            severity=None,
            crisis_score=0.0,
            matched_keyword=None,
            category=None,
        )