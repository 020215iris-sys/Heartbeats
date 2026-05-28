import torch

from session_validator import validate_output


FEW_SHOT_PROMPT = """### 명령어:
다음 상담 내용을 Heartbeat 포맷으로 요약하세요.
아래 형식만 출력하세요. 설명 금지.

### 예시 입력:
내담자: 요즘 술을 너무 많이 마시는 것 같아요. 스트레스 받으면 자꾸 마시게 되고.
상담사: 언제부터 그랬나요?
내담자: 한 6개월 됐어요.

### 예시 출력:
main_complaint:
음주 습관 조절 어려움과 스트레스 의존 지속

core_topics:
- 알코올의존
- 스트레스해소
- 자기통제

next_session_notes:
음주와 불안의 연결고리 탐색 필요

prompt_adjustment:
- addiction_support
- stress_management
- self_reflection

### 맥락:
{transcript}

### 답변:
"""


STOP_PATTERNS = [
    "상담사:",
    "내담자:",
    "맥락:",
    "### 맥락:",
    "### 명령어:"
]


def clean_output(text: str):

    if "### 답변:" in text:
        text = text.split("### 답변:")[-1].strip()

    lines = text.split("\n")

    cleaned = []

    for line in lines:

        should_stop = False

        for pattern in STOP_PATTERNS:
            if line.startswith(pattern):
                should_stop = True
                break

        if should_stop:
            break

        cleaned.append(line)

    return "\n".join(cleaned).strip()


def generate_summary(
    transcript,
    model,
    tokenizer,
    max_retry=2
):

    output = ""

    for attempt in range(max_retry):

        prompt = FEW_SHOT_PROMPT.format(
            transcript=transcript
        )

        inputs = tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=1024
        ).to("cuda")

        with torch.no_grad():

            outputs = model.generate(
                **inputs,
                max_new_tokens=120,
                do_sample=False,
                temperature=0.1,
                top_p=0.9,
                repetition_penalty=1.1,
                pad_token_id=tokenizer.eos_token_id,
                eos_token_id=tokenizer.eos_token_id
            )

        result = tokenizer.decode(
            outputs[0],
            skip_special_tokens=True
        )

        cleaned_result = clean_output(result)

        validation = validate_output(cleaned_result)

        if validation["pass"]:

            return {
                "success": True,
                "output": cleaned_result,
                "validation": validation
            }

        output = cleaned_result

    return {
        "success": False,
        "output": output,
        "validation": validation
    }