# import os
# import json
# import pandas as pd

# BASE_DIR = "data"

# TRANSCRIPT_DIR = os.path.join(BASE_DIR, "transcripts")
# YAML_DIR = os.path.join(BASE_DIR, "sample")

# MAPPING_PATH = os.path.join(BASE_DIR, "mapping.csv")
# OUTPUT_PATH = os.path.join(BASE_DIR, "train_dataset.jsonl")

# INSTRUCTION = "다음 상담 내용을 Heartbeat 포맷으로 요약하세요."

# df = pd.read_csv(MAPPING_PATH)

# dataset = []

# for _, row in df.iterrows():

#     transcript_path = os.path.join(
#         TRANSCRIPT_DIR,
#         row["source_file"]
#     )

#     yaml_path = os.path.join(
#         YAML_DIR,
#         row["yaml_file"]
#     )

#     with open(transcript_path, "r", encoding="utf-8") as f:
#         transcript = f.read()

#     with open(yaml_path, "r", encoding="utf-8") as f:
#         yaml_output = f.read()

#     sample = {
#         "instruction": INSTRUCTION,
#         "input": transcript,
#         "output": yaml_output
#     }

#     dataset.append(sample)

# with open(OUTPUT_PATH, "w", encoding="utf-8") as f:

#     for item in dataset:
#         f.write(
#             json.dumps(item, ensure_ascii=False)
#             + "\n"
#         )

# print(f"완료: {len(dataset)}개 저장됨")
# print(f"저장 위치: {OUTPUT_PATH}")

# import json

# with open("./data/train_dataset.jsonl", "r", encoding="utf-8") as f:
#     for i, line in enumerate(f):
#         print(json.loads(line))
#         print("---")
#         if i >= 1:
#             break

import json

cleaned = []
with open("./data/train_dataset_cleaned.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        data = json.loads(line)
        if data["output"].strip():  # output 비어있으면 제외
            cleaned.append(data)

with open("./data/train_dataset_cleaned.jsonl", "w", encoding="utf-8") as f:
    for item in cleaned:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")

print(f"총 {len(cleaned)}개 샘플 유지")