from ai.app.session_validator import parse_heartbeat_output

sample_output = """
심리적 부담감과 무기력함은 많은 사람들이 경험하는 문제입니다. 이러한 감정들은 다양한 원인에서 비롯될 수 있으며, 이를 해결하기 위해서는 전문가의 도움이 필요할 때도 있습니다. 내담자의 경우에는 직장에서의 스트레스와 관련된 심리적인 어려움일 가능성이 높습니다. 이에 대한 구체적인 평가를 위해 다음 세션에서는 더 깊이 있는 대화를 나누기로 했습니다.

"""

parsed = parse_heartbeat_output(sample_output)

print(parsed)

from ai.app.session_validator import fallback_parse

sample_output = """
심리적 부담감과 무기력함은 많은 사람들이 경험하는 문제입니다.
내담자는 직장 스트레스로 인해 정서적 소진을 경험하고 있습니다.
"""

parsed = fallback_parse(sample_output)

print(parsed)


from ai.app.continuity_prompt import build_continuity_prompt

previous_summary = """
main_complaint:
직장 스트레스로 인한 무기력감

core_topics:
- 직장스트레스
- 무기력감
"""

current_transcript = """
상담사: 지난주 이후 어떠셨어요?
내담자: 여전히 회사 가는 게 너무 힘들어요.
"""

prompt = build_continuity_prompt(
    previous_summary,
    current_transcript
)

print(prompt)


from ai.app.session_validator import fallback_parse
from ai.app.continuity_prompt import build_continuity_prompt

# ===== 가짜 LLM 출력 =====

llm_output = """
심리적 부담감과 무기력함은 많은 사람들이 경험하는 문제입니다.
내담자는 직장 스트레스로 인해 정서적 소진을 경험하고 있습니다.
"""

# ===== parser =====

parsed = fallback_parse(llm_output)

print("=== PARSED RESULT ===")
print(parsed)

# ===== continuity용 summary 생성 =====

summary_text = f"""
main_complaint:
{parsed['main_complaint']}

core_topics:
""" + "\n".join(
    [f"- {topic}" for topic in parsed["core_topics"]]
)

# ===== 다음 세션 transcript =====

next_transcript = """
상담사: 지난 상담 이후 어떠셨어요?
내담자: 회사에서 여전히 스트레스를 받고 있어요.
"""

# ===== continuity prompt 생성 =====

continuity_prompt = build_continuity_prompt(
    summary_text,
    next_transcript
)

print("\n=== CONTINUITY PROMPT ===")
print(continuity_prompt)