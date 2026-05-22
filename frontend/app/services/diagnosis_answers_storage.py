"""
설문 개별 답변 CSV 저장소 (MVP 임시 ver2).

diagnoses.csv가 평가 요약을 담는다면(ver1),
이 파일은 사용자가 각 문항에 어떻게 답했는지 원본을 저장한다.

활용 시나리오:
    - 자살 사고 문항(PHQ-9 9번) 같은 특정 문항을 위기 트리거로 사용
    - 점수 산정 방식 바뀌면 원본 답변으로 재계산 가능
    - 문항별 시간 추이 분석 (예: 수면 문제만 호전됐는지)
    - 임상 연구·감사 로그

ERD 매핑 제안 (백엔드 영역, 협의 필요):
    DIAGNOSIS_ANSWERS {
        uuid id PK
        uuid diagnosis_id FK
        uuid user_id
        string instrument_code
        integer question_number
        string question_text
        jsonb scores_for
        integer answer_score
        timestamp created_at
    }

CSV 컬럼:
    id              : 답변 레코드 UUID
    diagnosis_id    : diagnoses.csv의 부모 진단 ID
    user_id         : 사용자 UUID (비로그인이면 빈 값)
    instrument_code : 도구 식별자
    question_number : 1-based 문항 번호
    question_text   : 문항 텍스트 스냅샷 (placeholder가 바뀌어도 과거 답변 맥락 유지)
    scores_for_json : 이 문항이 기여한 질환들 (JSON 배열)
    answer_score    : 사용자가 선택한 점수
    created_at      : 저장 시각
"""

import csv
import json
import os
import uuid
from datetime import datetime, timezone


CSV_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "diagnosis_answers.csv",
)


FIELDNAMES = [
    "id",
    "diagnosis_id",
    "user_id",
    "instrument_code",
    "question_number",
    "question_text",
    "scores_for_json",
    "answer_score",
    "created_at",
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_file_exists() -> None:
    os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
    if not os.path.exists(CSV_PATH):
        with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=FIELDNAMES).writeheader()


def _deserialize(row: dict) -> dict:
    """CSV 행 → 사용하기 좋은 dict."""
    return {
        "id": row["id"],
        "diagnosis_id": row["diagnosis_id"],
        "user_id": row["user_id"] or None,
        "instrument_code": row["instrument_code"],
        "question_number": int(row["question_number"]),
        "question_text": row["question_text"],
        "scores_for": json.loads(row["scores_for_json"]),
        "answer_score": int(row["answer_score"]),
        "created_at": row["created_at"],
    }


# ========== 공개 API ==========


def save_answers(
    diagnosis_id: str,
    user_id: str | None,
    instrument: dict,
    answers: list[int],
) -> list[dict]:
    """
    한 진단의 모든 답변을 일괄 저장.

    instrument["questions"]와 answers는 같은 길이라고 가정 (라우트에서 보장).
    한 진단당 N개 행이 생성됨 (placeholder의 경우 10행).
    """
    _ensure_file_exists()
    now = _now()
    saved = []

    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)

        # 같은 진단의 모든 답변은 동일한 created_at을 공유 (한 트랜잭션)
        for i, (question, answer) in enumerate(
            zip(instrument["questions"], answers)
        ):
            record = {
                "id": str(uuid.uuid4()),
                "diagnosis_id": diagnosis_id,
                "user_id": user_id or "",
                "instrument_code": instrument["code"],
                "question_number": str(i + 1),
                # 문항 텍스트 스냅샷 — 나중에 placeholder가 PHQ-9으로 바뀌어도
                # 과거 진단의 "그때 본 문항 텍스트"는 보존됨
                "question_text": question["text"],
                "scores_for_json": json.dumps(
                    question["scores_for"], ensure_ascii=False
                ),
                "answer_score": str(answer),
                "created_at": now,
            }
            writer.writerow(record)
            saved.append(record)

    return saved


def find_answers_by_diagnosis(diagnosis_id: str) -> list[dict]:
    """한 진단의 모든 답변 (문항 순서대로)."""
    _ensure_file_exists()
    with open(CSV_PATH, "r", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    matching = [r for r in rows if r["diagnosis_id"] == diagnosis_id]
    matching.sort(key=lambda r: int(r["question_number"]))
    return [_deserialize(r) for r in matching]


def find_specific_answer(diagnosis_id: str, question_number: int) -> dict | None:
    """
    특정 진단의 특정 문항 답변.
    위기 트리거 처리에 사용 — 예: PHQ-9 9번(자살 사고) 점수만 빠르게 확인.
    """
    _ensure_file_exists()
    with open(CSV_PATH, "r", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if (
                row["diagnosis_id"] == diagnosis_id
                and int(row["question_number"]) == question_number
            ):
                return _deserialize(row)
    return None


def find_history_for_question(
    user_id: str,
    question_number: int,
) -> list[dict]:
    """
    한 사용자의 특정 문항 답변 추이 (최신순).
    예: "수면 문제(1번)가 시간에 따라 호전되고 있는지" 분석.
    """
    _ensure_file_exists()
    with open(CSV_PATH, "r", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    matching = [
        r for r in rows
        if r["user_id"] == user_id
        and int(r["question_number"]) == question_number
    ]
    matching.sort(key=lambda r: r["created_at"], reverse=True)
    return [_deserialize(r) for r in matching]