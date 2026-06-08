import os
import json
import pandas as pd

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

BASE_DIR = r"C:\IT\Final_project\heartbeats\ai"

MAPPING_FILE = os.path.join(
    BASE_DIR,
    "data",
    "mapping2.CSV"
)

TXT_DIR = os.path.join(
    BASE_DIR,
    "data",
    "transcripts_renamed"
)

YAML_DIR = os.path.join(
    BASE_DIR,
    "data",
    "sample_memory1"
)

OUTPUT_CSV = os.path.join(
    BASE_DIR,
    "data",
    "outputs",
    "memory_audit.csv"
)

mapping = pd.read_csv(MAPPING_FILE)
mapping = mapping.head(100)
print(mapping)

results = []

for idx, row in mapping.iterrows():

    txt_file = row["rename"]
    yaml_file = row["yaml_file"]

    txt_path = os.path.join(TXT_DIR, txt_file)
    yaml_path = os.path.join(YAML_DIR, yaml_file)

    if not os.path.exists(txt_path):
        continue

    if not os.path.exists(yaml_path):
        continue
    
    print(txt_file)
    print(yaml_file)
    print(txt_path)
    print(yaml_path)

    with open(txt_path, "r", encoding="utf-8") as f:
        transcript = f.read()

    with open(yaml_path, "r", encoding="utf-8") as f:
        yaml_text = f.read()

    prompt = f"""

당신은 Heartbeat 데이터셋 품질 검수자다.

목표:
상담 원문과 YAML을 비교하여
important_memory 품질을 평가하라.

반드시 아래 기준만 사용하라.

[Hallucination]

원문에 없는 사실

예시
- 승진했다고 없음
- 결혼 준비 스트레스 없음
- 불안 증가 없음

그런데 YAML에 있으면 Hallucination

[Missing]

important_memory는
향후 여러 회기에서도 계속 유효할
장기적 사실 정보만 저장한다.

다음은 missing으로 판단 가능:
- 수술
- 입원
- 진단
- 결혼
- 이혼
- 출산
- 가족 사망
- 직업 변화
- 승진
- 퇴사
- 장기 관계 변화
- 장기 생활환경 변화
- 반복적으로 언급되는 배경

다음은 missing으로 판단하지 말 것:
- 일시적 감정
- 특정 회기 고민
- 상담 통찰
- 성격 해석
- 현재 회기의 심리 상태
- 상담 목표

[Score]
점수 규칙

5:
Hallucination 없음
Missing 없음

4:
Missing 1~2개

3:
Missing 3~5개

2:
Missing 6개 이상
또는 Hallucination 1개 이상

1:
Hallucination 다수

0:
중대한 사실 대부분 누락

반드시 JSON만 출력

{{
  "score": 0,
  "hallucinations": [],
  "missing": [],
  "comment": ""
}}

[상담원문]

{transcript}

[YAML]

{yaml_text}
"""

    try:

        response = client.responses.create(
            model="gpt-4.1-mini",
            input=prompt
        )

        text = response.output_text

        result = json.loads(text)

        results.append({
            "txt_file": txt_file,
            "yaml_file": yaml_file,
            "score": result.get("score"),
            "hallucinations": json.dumps(
                result.get("hallucinations", []),
                ensure_ascii=False
            ),
            "missing": json.dumps(
                result.get("missing", []),
                ensure_ascii=False
            ),
            "comment": result.get("comment", "")
        })

        print(
            f"[{idx+1}/{len(mapping)}] 완료: {txt_file}"
        )

    except Exception as e:

        print(
            f"에러: {txt_file}"
        )

        print(e)

df = pd.DataFrame(results)

df.to_csv(
    OUTPUT_CSV,
    index=False,
    encoding="utf-8-sig"
)

print()
print("완료")
print(OUTPUT_CSV)