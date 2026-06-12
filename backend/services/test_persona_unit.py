import os
from openai import OpenAI
from dotenv import load_dotenv
from persona_service import build_persona_prompt

load_dotenv()

# ─────────────────────────────────────────
# 설정
# ─────────────────────────────────────────
GENERAL_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "../../ai/prompts/active/general_prompt.txt")
with open(GENERAL_PROMPT_PATH, "r", encoding="utf-8") as f:
    GENERAL_PROMPT = f.read()

client = OpenAI(
    api_key=os.getenv("CEREBRAS_API_KEY"),
    base_url="https://api.cerebras.ai/v1",
)

TEST_MESSAGE = "요즘 너무 힘들고 아무것도 하기 싫어요"

PERSONAS = [
    {
        "label": "🔵 기본 (params 없음)",
        "params": {}
    },
    {
        "label": "🟡 따뜻하고 친근함",
        "params": {"따듯함": 10, "공감도": 10, "전문성": 1, "말수":10, "말투":"반말"}
    },
    {
        "label": "🟠 차분하고 전문적",
        "params": {"따듯함": 1, "공감도": 1, "전문성": 10, "말수":1, "말투":"존댓말"}
    },
]

# ─────────────────────────────────────────
# 테스트
# ─────────────────────────────────────────
def test_persona(params: dict) -> str:
    persona_prompt = build_persona_prompt(params)
    system = GENERAL_PROMPT
    if persona_prompt:
        system += "\n\n" + persona_prompt

    res = client.chat.completions.create(
        model="gpt-oss-120b",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": TEST_MESSAGE},
        ]
    )
    return res.choices[0].message.content


def main():
    print(f"테스트 메시지: '{TEST_MESSAGE}'\n")
    print("=" * 60)

    for persona in PERSONAS:
        print(f"\n{persona['label']}")
        print(f"params: {persona['params']}")
        print("-" * 40)
        try:
            reply = test_persona(persona["params"])
            print(reply)
        except Exception as e:
            print(f"에러: {e}")
        print("=" * 60)
        
        import time
        time.sleep(8)  # ← 추가

if __name__ == "__main__":
    main()
