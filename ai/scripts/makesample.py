import os
import json
import openai
import re
from pathlib import Path

# ── 경로 설정 ──────────────────────────────────────────
RAW_DIR       = r"C:\Users\PC\Downloads\심리상담 샘플\Training\01.원천데이터\TS_002. 불안장애_0003. 3회기"
RENAMED_DIR   = r"C:\IT\Final_project\heartbeats\ai\data\transcripts_renamed"
YAML_DIR      = r"C:\IT\Final_project\heartbeats\ai\data\sample_memory1"
REVIEW_FILE   = r"C:\IT\Final_project\heartbeats\ai\data\review_v7.jsonl"

TARGET_COUNT   = 49

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

# ── 다음 인덱스 계산 ───────────────────────────────────
def get_next_index(renamed_dir):
    existing = [f for f in os.listdir(renamed_dir) if re.match(r"data_\d+\.txt", f)]
    if not existing:
        return 1
    nums = [int(re.search(r"data_(\d+)\.txt", f).group(1)) for f in existing]
    return max(nums) + 1

# ── 이미 처리된 원본 파일 목록 ─────────────────────────
def get_processed_sources(yaml_dir):
    """sample_xxx.yaml의 source 메타 읽기 (없으면 빈 set)"""
    processed = set()
    for yf in os.listdir(yaml_dir):
        meta_path = os.path.join(yaml_dir, yf.replace(".yaml", "_meta.txt"))
        if os.path.exists(meta_path):
            with open(meta_path, "r", encoding="utf-8") as f:
                processed.add(f.read().strip())
    return processed

# ── GPT로 JSON 생성 ────────────────────────────────────
SYSTEM_PROMPT = """당신은 심리상담 전문 요약 AI입니다.
상담 원문을 분석하여 반드시 아래 JSON 형식으로만 출력하세요.
다른 텍스트, 설명, 마크다운 없이 순수 JSON만 출력합니다.

{
  "main_complaint": "string",
  "core_topics": ["string", ...],
  "next_session_notes": "string",
  "prompt_adjustment": ["string", ...],
  "important_memory": ["string", ...]
}

important_memory 규칙:
- 원문에 명시된 사실만 기록
- 추론, 감정 해석, 원문에 없는 내용 절대 금지
- 사건, 관계 변화, 계획, 배경 사실 위주로 기록
- "내담자는" 같은 주어 접두어 없이 사실만 간결하게 기록
  예시) ❌ "내담자는 군산에 살고 있다" → ✅ "군산 본가 거주"
"""

def generate_summary(text):
    # 토큰 절약: 내담자 발화만 추출
    lines = text.split("\n")
    client_lines = [l for l in lines if "내담자" in l]
    compressed = "\n".join(client_lines)[:6000]  # 안전하게 자르기

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": compressed}
        ],
        temperature=0.1
    )
    raw = response.choices[0].message.content.strip()
    # JSON 파싱 검증
    parsed = json.loads(raw)
    return parsed

# ── 메인 ──────────────────────────────────────────────
def main():
    raw_files = sorted([
        f for f in os.listdir(RAW_DIR)
        if f.endswith(".txt")
    ])

    processed_sources = get_processed_sources(YAML_DIR)
    unprocessed = [f for f in raw_files if f not in processed_sources]

    print(f"미처리 원문: {len(unprocessed)}개 / 목표: {TARGET_COUNT}개")
    targets = unprocessed[:TARGET_COUNT]

    next_idx = get_next_index(RENAMED_DIR)
    results = []
    failed = []

    for i, raw_file in enumerate(targets):
        idx = next_idx + i
        idx_str = str(idx).zfill(3)

        raw_path     = os.path.join(RAW_DIR, raw_file)
        renamed_path = os.path.join(RENAMED_DIR, f"data_{idx_str}.txt")
        yaml_path    = os.path.join(YAML_DIR, f"sample_{idx_str}.yaml")
        meta_path    = os.path.join(YAML_DIR, f"sample_{idx_str}_meta.txt")

        print(f"[{i+1}/{len(targets)}] {raw_file} → data_{idx_str}.txt ... ", end="")

        try:
            with open(raw_path, "r", encoding="utf-8") as f:
                raw_text = f.read()

            summary = generate_summary(raw_text)

            # transcripts_renamed에 저장
            with open(renamed_path, "w", encoding="utf-8") as f:
                f.write(raw_text)

            # sample_memory1에 YAML 형식으로 저장 (기존 호환)
            yaml_lines = []
            yaml_lines.append(f"main_complaint:\n{summary['main_complaint']}")
            yaml_lines.append("core_topics:\n" + "\n".join(f"- {t}" for t in summary["core_topics"]))
            yaml_lines.append(f"next_session_notes:\n{summary['next_session_notes']}")
            yaml_lines.append("prompt_adjustment:\n" + "\n".join(f"- {t}" for t in summary["prompt_adjustment"]))
            yaml_lines.append("important_memory:\n" + "\n".join(f"- {m}" for m in summary["important_memory"]))

            with open(yaml_path, "w", encoding="utf-8") as f:
                f.write("\n".join(yaml_lines))

            # 원본 파일명 메타 저장 (중복 방지용)
            with open(meta_path, "w", encoding="utf-8") as f:
                f.write(raw_file)

            # 검수용 파일에 추가
            results.append({
                "source": raw_file,
                "input_preview": raw_text[:200],
                "output": summary
            })

            print("✓")

        except json.JSONDecodeError as e:
            print(f"✗ JSON 파싱 실패: {e}")
            failed.append(raw_file)
        except Exception as e:
            print(f"✗ 오류: {e}")
            failed.append(raw_file)

    # 검수용 파일 저장
    with open(REVIEW_FILE, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"\n완료: {len(results)}개 생성 / {len(failed)}개 실패")
    if failed:
        print(f"실패 목록: {failed}")
    print(f"검수 파일: {REVIEW_FILE}")

if __name__ == "__main__":
    main()