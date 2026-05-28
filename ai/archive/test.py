import asyncio
from ai.app.summary_generator import generate_summary

test_transcript = """
상담사: 요즘 어떠세요?
내담자: 회사 때문에 너무 지쳐있어요
"""

result = asyncio.run(
    generate_summary(test_transcript)
)

print(result)