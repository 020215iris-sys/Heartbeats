"""
진단 결과 CSV 저장소 (MVP 임시).

ERD의 DIAGNOSES 테이블에 대응되는 영역이지만,
placeholder가 다질환 구조라 점수·심각도 등을 JSON 직렬화해서 저장.
실제 도구(PHQ-9 등) 확정되면 컬럼 구조 재검토.

CSV 컬럼:
    id              : 진단 UUID
    user_id         : 사용자 UUID (비로그인이면 빈 값)
    instrument_code : 사용된 도구 식별자
    scores_json     : 질환별 점수 dict의 JSON 문자열
    severities_json : 질환별 심각도 정보 dict의 JSON 문자열
    follow_ups_json : 추가 설문 필요 질환 리스트의 JSON 문자열
    created_at      : 진단 시각 (UTC ISO 8601)
"""

import csv
import json
import os
import uuid
from datetime import datetime, timezone


CSV_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "diagnoses.csv",
)


FIELDNAMES = [
    "id",
    "user_id",
    "instrument_code",
    "scores_json",
    "severities_json",
    "follow_ups_json",
    "created_at",
]


def _now() -> str:
    """UTC ISO 8601 타임스탬프."""
    return datetime.now(timezone.utc).isoformat()


def _ensure_file_exists() -> None:
    """diagnoses.csv가 없으면 헤더만 있는 빈 파일 생성."""
    os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
    if not os.path.exists(CSV_PATH):
        with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=FIELDNAMES).writeheader()


def _deserialize(row: dict) -> dict:
    """
    CSV에서 읽은 raw 행의 JSON 필드들을 dict/list로 복원해 사용 편한 형태로.
    """
    return {
        "id": row["id"],
        # 빈 문자열은 None으로 변환 (CSV는 None 저장 못 함)
        "user_id": row["user_id"] or None,
        "instrument_code": row["instrument_code"],
        # JSON 문자열을 다시 Python 객체로
        "scores": json.loads(row["scores_json"]),
        "severities": json.loads(row["severities_json"]),
        "follow_ups": json.loads(row["follow_ups_json"]),
        "created_at": row["created_at"],
    }


# ========== 공개 API ==========


def save(
    user_id: str | None,
    instrument_code: str,
    scores: dict,
    severities: dict,
    follow_ups: list,
) -> dict:
    """
    진단 결과 저장. user_id가 None이면 비로그인 사용자(빈 문자열로 저장).

    반환: 저장된 레코드 dict (id 포함)
    """
    record = {
        "id": str(uuid.uuid4()),
        "user_id": user_id or "",
        "instrument_code": instrument_code,
        # ensure_ascii=False: 한글이 \uXXXX 식 escape 안 되게
        "scores_json": json.dumps(scores, ensure_ascii=False),
        "severities_json": json.dumps(severities, ensure_ascii=False),
        "follow_ups_json": json.dumps(follow_ups, ensure_ascii=False),
        "created_at": _now(),
    }

    _ensure_file_exists()
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=FIELDNAMES).writerow(record)

    # 호출자에게도 dict 형태로 돌려줌 (JSON 문자열이 아니라)
    return {
        "id": record["id"],
        "user_id": user_id,
        "instrument_code": instrument_code,
        "scores": scores,
        "severities": severities,
        "follow_ups": follow_ups,
        "created_at": record["created_at"],
    }


def find_latest_by_user(user_id: str) -> dict | None:
    """사용자의 가장 최근 진단. 없으면 None."""
    _ensure_file_exists()

    with open(CSV_PATH, "r", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    user_rows = [r for r in rows if r["user_id"] == user_id]
    if not user_rows:
        return None

    # created_at 최댓값 (ISO 8601 문자열이라 문자열 비교로 시간 정렬 됨)
    latest = max(user_rows, key=lambda r: r["created_at"])
    return _deserialize(latest)


def find_history_by_user(user_id: str) -> list[dict]:
    """사용자의 모든 진단 기록 (최신순). 추이 그래프용."""
    _ensure_file_exists()

    with open(CSV_PATH, "r", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    user_rows = [r for r in rows if r["user_id"] == user_id]
    user_rows.sort(key=lambda r: r["created_at"], reverse=True)

    return [_deserialize(r) for r in user_rows]


def find_by_id(diagnosis_id: str) -> dict | None:
    """진단 ID로 단건 조회. 추후 채팅 페이지가 이 진단 결과를 참조할 때 사용."""
    _ensure_file_exists()

    with open(CSV_PATH, "r", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["id"] == diagnosis_id:
                return _deserialize(row)
    return None