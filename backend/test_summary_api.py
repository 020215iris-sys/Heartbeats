from summary_service import request_summary


transcript = """
상담사: 요즘 어떠세요?
내담자: 너무 우울하고 아무것도 하기 싫어요.
"""


result = request_summary(transcript)

print(result)