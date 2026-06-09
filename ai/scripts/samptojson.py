# import os
# import json
# import csv

# yaml_dir = "./data/sample_memory1"
# output_path = "./data/train_dataset_nosession_v5.jsonl"
# instruction = "다음 상담 내용을 Heartbeat 포맷으로 요약하세요."

# mapping = {}
# with open("./data/mapping2.csv", "r", encoding="utf-8-sig") as f:
#     reader = csv.DictReader(f)
#     for row in reader:
#         mapping[row["yaml_file"]] = row["rename"]

# results = []
# for yaml_file, transcript_file in mapping.items():
#     yaml_path = os.path.join(yaml_dir, yaml_file)
#     transcript_path = os.path.join("./data/transcripts_renamed", transcript_file)

#     if not os.path.exists(yaml_path) or not os.path.exists(transcript_path):
#         print(f"파일 없음: {yaml_file} / {transcript_file}")
#         continue

#     # yaml 파싱 없이 plain text로 그냥 읽기
#     with open(yaml_path, "r", encoding="utf-8") as f:
#         output = f.read().strip()

#     with open(transcript_path, "r", encoding="utf-8") as f:
#         transcript = f.read().strip()

#     # session_id 줄 제거
#     lines = [l for l in output.split("\n") if not l.startswith("session_id")]
#     output = "\n".join(lines).strip()

#     results.append({
#         "instruction": instruction,
#         "input": transcript,
#         "output": output
#     })

# with open(output_path, "w", encoding="utf-8") as f:
#     for item in results:
#         f.write(json.dumps(item, ensure_ascii=False) + "\n")

# print(f"총 {len(results)}개 생성 완료")

## json 변환까지 추가한 버전

import os
import json

TXT_DIR = r"C:\IT\Final_project\heartbeats\ai\data\transcripts_renamed"
YAML_DIR = r"C:\IT\Final_project\heartbeats\ai\data\sample_memory1"
OUTPUT_FILE = r"C:\IT\Final_project\heartbeats\ai\data\train_dataset_v7.jsonl"

KEYS = ["main_complaint", "core_topics", "next_session_notes", "prompt_adjustment", "important_memory"]

def parse_custom_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    data = {k: [] for k in KEYS}
    current_key = None

    for line in lines:
        stripped = line.rstrip()
        
        # 키 감지
        matched_key = None
        for k in KEYS:
            if stripped == f"{k}:":
                matched_key = k
                break
        
        if matched_key:
            current_key = matched_key
            continue

        if current_key is None:
            continue

        # 리스트 항목
        if stripped.startswith("- "):
            data[current_key].append(stripped[2:].strip())
        # 단순 문자열 값
        elif stripped:
            if isinstance(data[current_key], list) and len(data[current_key]) == 0:
                data[current_key] = stripped
            else:
                data[current_key] = stripped

    # 단일 문자열이어야 할 필드 정리
    for k in ["main_complaint", "next_session_notes"]:
        if isinstance(data[k], list):
            data[k] = " ".join(data[k])

    return data

def main():
    yaml_files = sorted([f for f in os.listdir(YAML_DIR) if f.endswith(".yaml")])
    results = []
    skipped = []

    for yf in yaml_files:
        idx = yf.replace("sample_", "").replace(".yaml", "")
        tf = f"data_{idx}.txt"

        yaml_path = os.path.join(YAML_DIR, yf)
        txt_path  = os.path.join(TXT_DIR, tf)

        if not os.path.exists(txt_path):
            print(f"[SKIP] txt 없음: {tf}")
            skipped.append(yf)
            continue

        try:
            data = parse_custom_yaml(yaml_path)
            with open(txt_path, "r", encoding="utf-8") as f:
                input_text = f.read().strip()

            output = {
                "main_complaint": data["main_complaint"],
                "core_topics": data["core_topics"],
                "next_session_notes": data["next_session_notes"],
                "prompt_adjustment": data["prompt_adjustment"],
                "important_memory": data["important_memory"]
            }

            results.append({
                "input": input_text,
                "output": json.dumps(output, ensure_ascii=False)
            })

        except Exception as e:
            print(f"[SKIP] {yf} 오류: {e}")
            skipped.append(yf)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"\n완료: {len(results)}개 변환 / {len(skipped)}개 스킵")
    if skipped:
        print(f"스킵 목록: {skipped}")

if __name__ == "__main__":
    main()