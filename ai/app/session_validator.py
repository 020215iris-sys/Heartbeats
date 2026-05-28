# 문자열 최소길이 조정(짧아도 괜찮) / 한국어 비율 제거(외국어땜에 넣어놨는데 prompt_adjustment랑 충돌함)

import re

REQUIRED_KEYS = [
    "main_complaint",
    "core_topics",
    "next_session_notes",
    "prompt_adjustment"
]

FORBIDDEN_PATTERNS = [
    "심리적 부담감은",
    "다음은",
    "예시입니다",
    "포맷",
    "설명",
    "상담사:",
    "내담자:",
    "assistant",
    "user"
]

def validate_output(text: str) -> dict:
    result = {
        "pass": True,
        "errors": []
    }

    # 1. 필수 키 존재 여부
    for key in REQUIRED_KEYS:
        if key + ":" not in text:
            result["errors"].append(f"키 누락: {key}")
            result["pass"] = False

    # 2. 빈 값 여부
    for key in REQUIRED_KEYS:
        pattern = rf"{key}:\s*\n(\s*\n|$)"
        if re.search(pattern, text):
            result["errors"].append(f"빈 값: {key}")
            result["pass"] = False

    # 3. 리스트 키 확인
    for list_key in ["core_topics", "prompt_adjustment"]:
        if list_key + ":" in text:
            section = text.split(list_key + ":")[1].split("\n\n")[0]
            if "- " not in section:
                result["errors"].append(f"리스트 형식 아님: {list_key}")
                result["pass"] = False

    # 4. 문자열 최소 길이
    if "main_complaint:" in text:
        val = text.split("main_complaint:")[1].split("\n\n")[0].strip()
        if len(val) < 5:
            result["errors"].append("main_complaint 너무 짧음")
            result["pass"] = False

    # # 5. 한국어 비율 --------------------------------------------- prompt_adjustment랑 충돌
    # korean_chars = len(re.findall(r'[가-힣]', text))
    # total_chars = len(text.replace(" ", "").replace("\n", ""))
    # if total_chars > 0 and korean_chars / total_chars < 0.3:
    #     result["errors"].append("한국어 비율 낮음")
    #     result["pass"] = False

    # 6. forbidden pattern
    for pattern in FORBIDDEN_PATTERNS:
        if pattern in text:
            result["errors"].append(f"금지 패턴 감지: {pattern}")
            result["pass"] = False

    return result