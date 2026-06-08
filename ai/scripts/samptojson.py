import os
import json
import csv

yaml_dir = "./data/sample_memory1"
output_path = "./data/train_dataset_nosession_v4_100.jsonl"
instruction = "다음 상담 내용을 Heartbeat 포맷으로 요약하세요."

mapping = {}
with open("./data/mapping2.csv", "r", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for row in reader:
        mapping[row["yaml_file"]] = row["rename"]

results = []
for yaml_file, transcript_file in mapping.items():
    yaml_path = os.path.join(yaml_dir, yaml_file)
    transcript_path = os.path.join("./data/transcripts_renamed", transcript_file)

    if not os.path.exists(yaml_path) or not os.path.exists(transcript_path):
        print(f"파일 없음: {yaml_file} / {transcript_file}")
        continue

    # yaml 파싱 없이 plain text로 그냥 읽기
    with open(yaml_path, "r", encoding="utf-8") as f:
        output = f.read().strip()

    with open(transcript_path, "r", encoding="utf-8") as f:
        transcript = f.read().strip()

    # session_id 줄 제거
    lines = [l for l in output.split("\n") if not l.startswith("session_id")]
    output = "\n".join(lines).strip()

    results.append({
        "instruction": instruction,
        "input": transcript,
        "output": output
    })

with open(output_path, "w", encoding="utf-8") as f:
    for item in results:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")

print(f"총 {len(results)}개 생성 완료")

import json
cnt=0
with open('./data/train_dataset_nosession_v4_100.jsonl', encoding='utf-8') as f:
    for i,line in enumerate(f,1):
        json.loads(line)
        cnt+=1
print('OK', cnt)