def build_prompt(
    strategy,
    previous_summary=None
):

    prompt = ""

    if previous_summary:

        prompt += f"""
이전 상담 요약:

{previous_summary}

"""

    if strategy == "crisis":

        prompt += """
위기 상황 우선
안전 확인 우선
짧은 응답
"""

    elif strategy == "anxiety":

        prompt += """
불안 원인 탐색
걱정 패턴 확인
"""

    elif strategy == "depression":

        prompt += """
무기력 원인 탐색
자기비난 확인
"""

    else:

        prompt += """
일반 감정 탐색
"""

    return prompt