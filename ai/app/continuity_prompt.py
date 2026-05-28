def build_continuity_prompt(previous_summary, current_transcript):

    prompt = f"""
이전 세션 요약:
{previous_summary}

현재 상담 내용:
{current_transcript}

이전 세션 내용을 참고하여
현재 상담 내용을 요약하세요.

출력 형식:

main_complaint:

core_topics:
- 항목1
- 항목2

next_session_notes:

prompt_adjustment:
- 태그1
- 태그2
"""

    return prompt